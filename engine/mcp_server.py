"""
mcp_server.py -- AI Memory System MCP Server
=============================================
Exposes all memory engine capabilities as MCP tools.
Any MCP-compatible client (WorkBuddy, Claude Desktop, etc.)
can call these tools directly -- no HTTP or manual copy-paste needed.

Tools exposed:
  Memory (LTM):
    memory_save       -- save a new long-term memory entry
    memory_recall     -- search long-term memory by keyword
    memory_get        -- get a single entry by ID
    memory_update     -- update an existing entry
    memory_delete     -- delete an entry (requires confirm=true)
    memory_profile    -- get user profile summary
    memory_list       -- list all entries, optionally filtered by category

  Knowledge Base (KB):
    kb_add            -- add a new knowledge base entry
    kb_search         -- search the knowledge base
    kb_update         -- update a KB entry
    kb_delete         -- delete a KB entry
    kb_index          -- list KB index (no full content)
    kb_import         -- bulk-import large text into KB

  Session (STM):
    session_start     -- start a new conversation session
    session_update    -- update session context key/value
    session_event     -- log an event to the session timeline
    session_queue     -- queue an item for pending save
    session_pending   -- get all pending saves in current session
    session_end       -- end session and get summary

  Status:
    memory_status     -- get overall system status and stats

Usage:
  python mcp_server.py                  # stdio mode (default, for WorkBuddy)
  python mcp_server.py --sse            # SSE mode (for network clients)
  python mcp_server.py --port 8766      # custom port (SSE mode)
"""

from __future__ import annotations

import argparse
import os
import sys

# ── Windows UTF-8 fix ──────────────────────────────────────────────────────────
# Ensure stdin/stdout/stderr use UTF-8 on Windows (avoids GBK errors in MCP mode)
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from typing import Any

# ── Path bootstrap ─────────────────────────────────────────────────────────────
# Allow running from any working directory
_HERE = Path(__file__).parent.resolve()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# ── Engine imports ──────────────────────────────────────────────────────────────
from config import MEMORY_DIR, SECURE_DIR
from core.ltm import LTMManager, LTMError
from core.kb import KBManager, KBError
from core.stm import STMManager, STMError
from core.trigger import TriggerEngine
from security.detector import SensitiveDetector
from security.encryptor import Encryptor

# ── MCP imports ─────────────────────────────────────────────────────────────────
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

# ── Singletons ──────────────────────────────────────────────────────────────────
# Share the same encryptor + detector instances as the FastAPI layer would,
# so encryption behavior is consistent regardless of which interface is used.
_enc  = Encryptor(Path(SECURE_DIR))
_det  = SensitiveDetector()
_ltm  = LTMManager(Path(MEMORY_DIR), encryptor=_enc, detector=_det)
_kb   = KBManager(Path(MEMORY_DIR))
_stm  = STMManager()
_trig = TriggerEngine()

# MCP server instance
server = Server("ai-memory-system")


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _ok(data: Any) -> list[types.TextContent]:
    """Wrap a successful result as MCP text content."""
    import json
    if isinstance(data, str):
        return [types.TextContent(type="text", text=data)]
    return [types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


def _err(msg: str) -> list[types.TextContent]:
    """Wrap an error message as MCP text content."""
    import json
    return [types.TextContent(type="text", text=json.dumps({"error": msg}, ensure_ascii=False))]


def _entry_dict(entry) -> dict:
    """Convert a dataclass entry to a plain dict."""
    from dataclasses import asdict
    return asdict(entry)


# ─────────────────────────────────────────────────────────────────────────────
# Tool Declarations
# ─────────────────────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [

        # ── Long-Term Memory ──────────────────────────────────────────────────

        types.Tool(
            name="memory_save",
            description=(
                "Save a new entry to long-term memory (LTM). "
                "Use this when the user shares personal information, preferences, "
                "project details, decisions, habits, or any content worth remembering "
                "across conversations. Sensitive data is auto-detected and redacted."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content":    {"type": "string",  "description": "The memory content to save."},
                    "category":   {"type": "string",  "description": "One of: profile, preference, project, decision, habit, credential, other", "default": "other"},
                    "source":     {"type": "string",  "description": "One of: user-explicit, ai-detected, user-upload", "default": "ai-detected"},
                    "tags":       {"type": "array",   "items": {"type": "string"}, "description": "Optional list of tags.", "default": []},
                    "passphrase": {"type": "string",  "description": "Optional. If provided, sensitive values are encrypted with this passphrase."},
                },
                "required": ["content"],
            },
        ),

        types.Tool(
            name="memory_recall",
            description=(
                "Search long-term memory by keyword. "
                "Use this at the start of every conversation to load relevant context, "
                "or when the user asks about past conversations, preferences, or projects."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query":       {"type": "string",  "description": "Search keyword or phrase."},
                    "category":    {"type": "string",  "description": "Optional category filter."},
                    "max_results": {"type": "integer", "description": "Max entries to return (default 20).", "default": 20},
                },
                "required": ["query"],
            },
        ),

        types.Tool(
            name="memory_get",
            description="Retrieve a single long-term memory entry by its exact ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {"type": "string", "description": "The LTM entry ID (UUID)."},
                },
                "required": ["entry_id"],
            },
        ),

        types.Tool(
            name="memory_update",
            description="Update the content, tags, or category of an existing LTM entry.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {"type": "string", "description": "The LTM entry ID to update."},
                    "content":  {"type": "string", "description": "New content (omit to keep current)."},
                    "tags":     {"type": "array",  "items": {"type": "string"}, "description": "New tags (omit to keep current)."},
                    "category": {"type": "string", "description": "New category (omit to keep current)."},
                },
                "required": ["entry_id"],
            },
        ),

        types.Tool(
            name="memory_delete",
            description=(
                "Delete a long-term memory entry. "
                "IMPORTANT: confirm must be set to true to actually execute the deletion. "
                "Always confirm with the user before calling this."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {"type": "string",  "description": "The LTM entry ID to delete."},
                    "confirm":  {"type": "boolean", "description": "Must be true to execute. Safety guard.", "default": False},
                },
                "required": ["entry_id"],
            },
        ),

        types.Tool(
            name="memory_profile",
            description=(
                "Get a structured summary of the user profile from long-term memory. "
                "Call this at the start of every conversation to personalize responses."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),

        types.Tool(
            name="memory_list",
            description="List all long-term memory entries, optionally filtered by category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string",  "description": "Optional category filter."},
                    "limit":    {"type": "integer", "description": "Max entries (default 100).", "default": 100},
                },
            },
        ),

        # ── Knowledge Base ────────────────────────────────────────────────────

        types.Tool(
            name="kb_add",
            description=(
                "Add a new entry to the knowledge base. "
                "Use for technical docs, user-uploaded content, AI-learned facts, "
                "project specs, or any reference material the user wants preserved."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "title":      {"type": "string", "description": "Short descriptive title for the entry."},
                    "content":    {"type": "string", "description": "Full content of the entry."},
                    "category":   {"type": "string", "description": "One of: personal, technical, project, domain, reference, ai-learned", "default": "personal"},
                    "tags":       {"type": "array",  "items": {"type": "string"}, "description": "Optional tags.", "default": []},
                    "source":     {"type": "string", "description": "One of: user-upload, user-typed, ai-extracted, ai-learned", "default": "user-typed"},
                    "confidence": {"type": "string", "description": "One of: high, medium, low", "default": "high"},
                    "confirmed":  {"type": "boolean","description": "Whether the user has confirmed this entry.", "default": True},
                },
                "required": ["title", "content"],
            },
        ),

        types.Tool(
            name="kb_search",
            description=(
                "Search the knowledge base by keyword. "
                "Use when the user references a topic, asks a question, "
                "or when relevant background knowledge might improve the response."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query":          {"type": "string",  "description": "Search keyword or phrase."},
                    "category":       {"type": "string",  "description": "Optional category filter."},
                    "top_k":          {"type": "integer", "description": "Max results (default 5).", "default": 5},
                    "confirmed_only": {"type": "boolean", "description": "Only return confirmed entries (default true).", "default": True},
                },
                "required": ["query"],
            },
        ),

        types.Tool(
            name="kb_update",
            description="Update title, content, tags, or confirmation status of a KB entry.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id":  {"type": "string",  "description": "The KB entry ID to update."},
                    "title":     {"type": "string",  "description": "New title (omit to keep current)."},
                    "content":   {"type": "string",  "description": "New content (omit to keep current)."},
                    "tags":      {"type": "array",   "items": {"type": "string"}, "description": "New tags (omit to keep current)."},
                    "confirmed": {"type": "boolean", "description": "Update confirmation status."},
                },
                "required": ["entry_id"],
            },
        ),

        types.Tool(
            name="kb_delete",
            description="Delete a knowledge base entry. confirm must be true to execute.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entry_id": {"type": "string",  "description": "The KB entry ID to delete."},
                    "confirm":  {"type": "boolean", "description": "Must be true to execute.", "default": False},
                },
                "required": ["entry_id"],
            },
        ),

        types.Tool(
            name="kb_index",
            description=(
                "Get a lightweight index of all knowledge base entries (titles and metadata, "
                "no full content). Use to browse available knowledge without loading everything."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),

        types.Tool(
            name="kb_import",
            description=(
                "Bulk-import a large text document into the knowledge base. "
                "The text is automatically split into paragraphs and saved as separate entries. "
                "Use when the user pastes documentation, notes, or any large reference material."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text":         {"type": "string", "description": "The full text to import."},
                    "category":     {"type": "string", "description": "Category for all imported entries.", "default": "reference"},
                    "source":       {"type": "string", "description": "Source label.", "default": "user-upload"},
                    "title_prefix": {"type": "string", "description": "Prefix for auto-generated titles.", "default": "Imported"},
                },
                "required": ["text"],
            },
        ),

        # ── Session (STM) ─────────────────────────────────────────────────────

        types.Tool(
            name="session_start",
            description=(
                "Start a new short-term memory session. "
                "Call this at the beginning of every conversation to enable "
                "in-session context tracking and pending save queuing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "description": "One of: conversation, coding, project, research, writing, analysis, general",
                        "default": "conversation",
                    },
                },
            },
        ),

        types.Tool(
            name="session_update",
            description="Update a key-value pair in the active session's context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID returned by session_start."},
                    "key":        {"type": "string", "description": "Context key, e.g. 'current_project'."},
                    "value":      {"description": "Value to store (any JSON-serializable type)."},
                },
                "required": ["session_id", "key", "value"],
            },
        ),

        types.Tool(
            name="session_event",
            description="Log a notable event to the session timeline (e.g. memory trigger, user correction).",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id":  {"type": "string", "description": "Session ID."},
                    "event_type":  {"type": "string", "description": "One of: memory_trigger, intent_detected, user_correction, milestone"},
                    "content":     {"type": "string", "description": "Event description."},
                },
                "required": ["session_id", "event_type", "content"],
            },
        ),

        types.Tool(
            name="session_queue",
            description=(
                "Queue an item for pending save to LTM or KB. "
                "Use when AI detects memory-worthy content mid-conversation "
                "and wants to save it after user confirmation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id":   {"type": "string", "description": "Session ID."},
                    "content":      {"type": "string", "description": "Content to save."},
                    "category":     {"type": "string", "description": "Memory category.", "default": "other"},
                    "source":       {"type": "string", "description": "Source label.", "default": "ai-detected"},
                    "destination":  {"type": "string", "description": "One of: ltm, kb", "default": "ltm"},
                },
                "required": ["session_id", "content"],
            },
        ),

        types.Tool(
            name="session_pending",
            description="Get all items queued for saving in the current session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID."},
                },
                "required": ["session_id"],
            },
        ),

        types.Tool(
            name="session_end",
            description=(
                "End the current session and get a summary. "
                "Call at conversation end to flush pending saves and clean up STM. "
                "Set auto_flush=true to automatically write all pending_saves to LTM/KB. "
                "Returns a summary with all pending_saves the AI should process."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id":  {"type": "string",  "description": "Session ID to end."},
                    "auto_flush":  {"type": "boolean", "description": "If true, auto-write pending_saves to LTM/KB.", "default": False},
                },
                "required": ["session_id"],
            },
        ),

        # ── Status ────────────────────────────────────────────────────────────

        types.Tool(
            name="memory_status",
            description=(
                "Get overall memory system status: entry counts, active sessions, "
                "system health. Use for diagnostics or when user asks about memory."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="trigger_analyze",
            description=(
                "Analyze text (or a session's events) for memory-worthy content. "
                "Returns a list of save suggestions with confidence scores — does NOT "
                "automatically save anything. Call this at conversation end or when "
                "unsure what to save. Human/AI confirms before actual saving."
                "\n\n分析文本，识别值得保存的记忆内容。返回建议列表（不自动写入）。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to analyze for save suggestions.",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Optional: analyze events from an active session instead of raw text.",
                    },
                },
            },
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Tool Handlers
# ─────────────────────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Route incoming tool calls to the appropriate handler."""

    # ── Long-Term Memory ──────────────────────────────────────────────────────

    if name == "memory_save":
        try:
            entry = _ltm.save(
                content    = arguments["content"],
                category   = arguments.get("category", "other"),
                source     = arguments.get("source", "ai-detected"),
                tags       = arguments.get("tags", []),
                passphrase = arguments.get("passphrase"),
            )
            result = {
                "status":  "saved",
                "entry_id": entry.id,
                "category": entry.category,
                "sensitive": entry.sensitive,
                "created_at": entry.created_at,
            }
            return _ok(result)
        except (ValueError, LTMError) as exc:
            return _err(str(exc))

    if name == "memory_recall":
        entries = _ltm.search(
            query       = arguments["query"],
            category    = arguments.get("category"),
            max_results = arguments.get("max_results", 20),
        )
        return _ok([_entry_dict(e) for e in entries])

    if name == "memory_get":
        entry = _ltm.get(arguments["entry_id"])
        if entry is None:
            return _err(f"Entry '{arguments['entry_id']}' not found.")
        return _ok(_entry_dict(entry))

    if name == "memory_update":
        try:
            entry = _ltm.update(
                entry_id = arguments["entry_id"],
                content  = arguments.get("content"),
                tags     = arguments.get("tags"),
                category = arguments.get("category"),
            )
            return _ok({"status": "updated", "entry": _entry_dict(entry)})
        except (LTMError, ValueError) as exc:
            return _err(str(exc))

    if name == "memory_delete":
        try:
            deleted = _ltm.delete(
                entry_id = arguments["entry_id"],
                confirm  = arguments.get("confirm", False),
            )
            return _ok({"status": "deleted" if deleted else "not_found", "entry_id": arguments["entry_id"]})
        except ValueError as exc:
            return _err(str(exc))

    if name == "memory_profile":
        return _ok(_ltm.load_profile())

    if name == "memory_list":
        entries = _ltm.list_all(
            category = arguments.get("category"),
            limit    = arguments.get("limit", 100),
        )
        return _ok([_entry_dict(e) for e in entries])

    # ── Knowledge Base ────────────────────────────────────────────────────────

    if name == "kb_add":
        try:
            entry = _kb.add(
                title      = arguments["title"],
                content    = arguments["content"],
                category   = arguments.get("category", "personal"),
                tags       = arguments.get("tags", []),
                source     = arguments.get("source", "user-typed"),
                confidence = arguments.get("confidence", "high"),
                confirmed  = arguments.get("confirmed", True),
            )
            return _ok({"status": "added", "entry_id": entry.id, "title": entry.title})
        except (ValueError, KBError) as exc:
            return _err(str(exc))

    if name == "kb_search":
        entries = _kb.search(
            query          = arguments["query"],
            category       = arguments.get("category"),
            top_k          = arguments.get("top_k", 5),
            confirmed_only = arguments.get("confirmed_only", True),
        )
        return _ok([_entry_dict(e) for e in entries])

    if name == "kb_update":
        try:
            entry = _kb.update(
                entry_id  = arguments["entry_id"],
                title     = arguments.get("title"),
                content   = arguments.get("content"),
                tags      = arguments.get("tags"),
                confirmed = arguments.get("confirmed"),
            )
            return _ok({"status": "updated", "entry_id": entry.id})
        except (KBError, ValueError) as exc:
            return _err(str(exc))

    if name == "kb_delete":
        try:
            deleted = _kb.delete(
                entry_id = arguments["entry_id"],
                confirm  = arguments.get("confirm", False),
            )
            return _ok({"status": "deleted" if deleted else "not_found"})
        except ValueError as exc:
            return _err(str(exc))

    if name == "kb_index":
        return _ok(_kb.get_index())

    if name == "kb_import":
        try:
            entries = _kb.import_text(
                text         = arguments["text"],
                category     = arguments.get("category", "reference"),
                source       = arguments.get("source", "user-upload"),
                title_prefix = arguments.get("title_prefix", "Imported"),
            )
            return _ok({
                "status":         "imported",
                "entries_created": len(entries),
                "ids":            [e.id for e in entries],
            })
        except (ValueError, KBError) as exc:
            return _err(str(exc))

    # ── Session (STM) ─────────────────────────────────────────────────────────

    if name == "session_start":
        session = _stm.start_session(
            task_type = arguments.get("task_type", "conversation")
        )
        return _ok({
            "session_id": session.session_id,
            "task_type":  session.task_type,
            "started_at": session.started_at,
            "status":     "active",
        })

    if name == "session_update":
        ok = _stm.update_context(
            session_id = arguments["session_id"],
            key        = arguments["key"],
            value      = arguments["value"],
        )
        return _ok({"status": "updated" if ok else "session_not_found"})

    if name == "session_event":
        ok = _stm.add_event(
            session_id = arguments["session_id"],
            event_type = arguments["event_type"],
            content    = arguments["content"],
        )
        return _ok({"status": "logged" if ok else "session_not_found"})

    if name == "session_queue":
        ok = _stm.queue_save(
            session_id = arguments["session_id"],
            item = {
                "content":     arguments["content"],
                "category":    arguments.get("category", "other"),
                "source":      arguments.get("source", "ai-detected"),
                "destination": arguments.get("destination", "ltm"),
            },
        )
        return _ok({"status": "queued" if ok else "session_not_found"})

    if name == "session_pending":
        pending = _stm.get_pending_saves(arguments["session_id"])
        return _ok({"pending_saves": pending, "count": len(pending)})

    if name == "session_end":
        try:
            summary = _stm.end_session(arguments["session_id"])
        except STMError as exc:
            return _err(str(exc))

        flushed: list[dict] = []
        flush_errors: list[dict] = []

        if arguments.get("auto_flush") and summary.get("pending_saves"):
            for item in summary["pending_saves"]:
                dest = item.get("destination", "ltm")
                try:
                    if dest == "kb":
                        entry = _kb.add(
                            title=item.get("content", "")[:60],
                            content=item["content"],
                            category=item.get("category", "personal"),
                            source=item.get("source", "ai-detected"),
                        )
                        flushed.append({"destination": "kb", "entry_id": entry.id})
                    else:
                        entry = _ltm.save(
                            content=item["content"],
                            category=item.get("category", "other"),
                            source=item.get("source", "ai-detected"),
                        )
                        flushed.append({"destination": "ltm", "entry_id": entry.id})
                except Exception as exc:
                    flush_errors.append({
                        "content_preview": item.get("content", "")[:40],
                        "error": str(exc),
                    })

        summary["auto_flushed"] = flushed
        summary["flush_errors"] = flush_errors
        return _ok(summary)

    # ── Status ────────────────────────────────────────────────────────────────

    if name == "memory_status":
        ltm_entries = _ltm.list_all(limit=9999)
        kb_entries  = _kb.get_index()
        active_sess = _stm.list_active_sessions()

        sensitive_count = sum(1 for e in ltm_entries if e.sensitive)
        kb_by_cat: dict[str, int] = {}
        for e in kb_entries:
            kb_by_cat[e["category"]] = kb_by_cat.get(e["category"], 0) + 1

        return _ok({
            "system":         "ai-memory-system",
            "version":        "1.0.0",
            "memory_dir":     str(MEMORY_DIR),
            "ltm": {
                "total_entries":     len(ltm_entries),
                "sensitive_entries": sensitive_count,
            },
            "kb": {
                "total_entries": len(kb_entries),
                "by_category":   kb_by_cat,
            },
            "stm": {
                "active_sessions": len(active_sess),
                "sessions":        active_sess,
            },
        })

    if name == "trigger_analyze":
        text = arguments.get("text", "")
        session_id = arguments.get("session_id", "")

        if session_id:
            session = _stm.get_session(session_id)
            if session is None:
                return _err(f"Session '{session_id}' not found.")
            events = [
                {"event_type": e.event_type, "content": e.content}
                for e in session.events
            ]
            suggestions = _trig.analyze(events)
        elif text:
            suggestions = _trig.analyze_text(text)
        else:
            return _err("Provide either 'text' or 'session_id'.")

        return _ok({
            "suggestion_count": len(suggestions),
            "suggestions": [
                {
                    "content":     s.content,
                    "destination": s.destination,
                    "category":    s.category,
                    "confidence":  round(s.confidence, 2),
                    "reason":      s.reason,
                    "tags":        s.tags,
                }
                for s in suggestions
            ],
        })

    # ── Unknown tool ──────────────────────────────────────────────────────────
    return _err(f"Unknown tool: {name}")


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

async def _run_stdio() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    import asyncio
    parser = argparse.ArgumentParser(description="AI Memory System MCP Server")
    parser.add_argument("--sse",  action="store_true", help="Run in SSE mode (HTTP) instead of stdio")
    parser.add_argument("--port", type=int, default=8766, help="Port for SSE mode (default: 8766)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for SSE mode (default: 127.0.0.1)")
    args = parser.parse_args()

    if args.sse:
        # SSE / HTTP mode
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        import uvicorn

        sse_transport = SseServerTransport("/messages/")

        async def handle_sse(request):
            async with sse_transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await server.run(
                    streams[0], streams[1],
                    server.create_initialization_options(),
                )

        starlette_app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse_transport.handle_post_message),
            ]
        )

        print(f"[AI Memory MCP] SSE mode: http://{args.host}:{args.port}/sse")
        uvicorn.run(starlette_app, host=args.host, port=args.port)
    else:
        # Default: stdio mode (for WorkBuddy / Claude Desktop)
        print("[AI Memory MCP] stdio mode — ready", file=sys.stderr)
        asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()

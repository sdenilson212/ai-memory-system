"""
mcp_server_wal.py -- AI Memory System MCP Server (WAL-enhanced)
===============================================================
WAL 增强版 MCP 服务器，提供增量写入性能优化。

特性:
    1. 完全兼容原有 API 和工具
    2. 内部使用 WAL 增量写入，大幅提升保存性能
    3. 自动后台合并，不影响用户体验
    4. 可配置 WAL 参数

性能对比:
    - 传统方式: 每次保存 O(n) 重写整个文件
    - WAL 方式: 每次保存 O(1) 追加到日志文件
    - 性能提升: 10-100 倍 (取决于条目数量)

使用方式:
    python mcp_server_wal.py                  # stdio 模式 (默认)
    python mcp_server_wal.py --sse            # SSE 模式
    python mcp_server_wal.py --port 8766      # 自定义端口

配置环境变量:
    AI_MEMORY_WAL_ENABLED=1          # 启用 WAL (默认 True)
    AI_MEMORY_WAL_THRESHOLD=100      # 合并阈值 (默认 100)
    AI_MEMORY_WAL_INTERVAL=300       # 合并间隔秒数 (默认 300)
    AI_MEMORY_WAL_MAX_SIZE=10485760  # 最大 WAL 文件大小 (默认 10MB)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ── Windows UTF-8 fix ──────────────────────────────────────────────────────────
# Ensure stdin/stdout/stderr use UTF-8 on Windows (avoids GBK errors in MCP mode)
if sys.platform == "win32":
    import io
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# ── Paths ─────────────────────────────────────────────────────────────────────
# Workspace root: the directory containing this script's parent
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parent
MEMORY_DIR = WORKSPACE_ROOT / "memory-bank"
SECURE_DIR = MEMORY_DIR / "secure"

# ── Dependencies ──────────────────────────────────────────────────────────────
try:
    from mcp.server import Server
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️ MCP SDK not installed. Run: pip install mcp")
    sys.exit(1)

try:
    from pathlib import Path
    
    # 导入 WAL 增强版 LTMManager
    from core.ltm_wal import LTMManagerWAL
    
    # 其他管理器
    from core.kb import KBManager
    from core.stm import STMManager
    from core.trigger import TriggerEngine
    
    from security.encryptor import Encryptor
    from security.detector import SensitiveDetector
    
except ImportError as e:
    print(f"⚠️ Failed to import memory engine modules: {e}")
    print("Make sure you're running from the engine/ directory.")
    sys.exit(1)

# ── Configuration ─────────────────────────────────────────────────────────────
# 从环境变量读取 WAL 配置
WAL_ENABLED = os.environ.get("AI_MEMORY_WAL_ENABLED", "1").lower() in ("1", "true", "yes")
WAL_THRESHOLD = int(os.environ.get("AI_MEMORY_WAL_THRESHOLD", "100"))
WAL_INTERVAL = int(os.environ.get("AI_MEMORY_WAL_INTERVAL", "300"))
WAL_MAX_SIZE = int(os.environ.get("AI_MEMORY_WAL_MAX_SIZE", str(10 * 1024 * 1024)))  # 10MB

print(f"🧠 AI Memory System MCP Server (WAL-enhanced)")
print(f"📁 Memory directory: {MEMORY_DIR}")
print(f"⚡ WAL enabled: {WAL_ENABLED}")
if WAL_ENABLED:
    print(f"   - Merge threshold: {WAL_THRESHOLD} records")
    print(f"   - Merge interval: {WAL_INTERVAL} seconds")
    print(f"   - Max WAL size: {WAL_MAX_SIZE // 1024 // 1024} MB")

# ── Singletons ────────────────────────────────────────────────────────────────
# Share the same encryptor + detector instances as the FastAPI layer would,
# so encryption behavior is consistent regardless of which interface is used.
_enc = Encryptor(Path(SECURE_DIR))
_det = SensitiveDetector()

# 使用 WAL 增强版 LTMManager
_ltm = LTMManagerWAL(
    Path(MEMORY_DIR), 
    encryptor=_enc, 
    detector=_det,
    enable_wal=WAL_ENABLED,
    wal_merge_threshold=WAL_THRESHOLD,
    wal_merge_interval=WAL_INTERVAL,
    wal_max_size=WAL_MAX_SIZE,
)

_kb = KBManager(Path(MEMORY_DIR))
_stm = STMManager()
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
# Tool Declarations (与原版完全一致)
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
                    "content":  {"type": "string", "description": "New content (optional)."},
                    "tags":     {"type": "array",  "items": {"type": "string"}, "description": "New tags (optional)."},
                    "category": {"type": "string", "description": "New category (optional)."},
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
                    "entry_id": {"type": "string", "description": "The LTM entry ID to delete."},
                    "confirm":  {"type": "boolean", "description": "Must be true to execute deletion.", "default": False},
                },
                "required": ["entry_id", "confirm"],
            },
        ),

        types.Tool(
            name="memory_profile",
            description="Get a structured summary of the user profile from long-term memory. Call this at the start of every conversation to personalize responses.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),

        types.Tool(
            name="memory_list",
            description="List all long-term memory entries, optionally filtered by category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Optional category filter."},
                    "limit":    {"type": "integer", "description": "Maximum entries to list (default 100).", "default": 100},
                },
                "required": [],
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
                    "title":   {"type": "string", "description": "Title of the knowledge entry."},
                    "content": {"type": "string", "description": "Full content of the entry."},
                    "tags":    {"type": "array",  "items": {"type": "string"}, "description": "Optional tags.", "default": []},
                    "category": {"type": "string", "description": "Category (e.g., technical, project, reference).", "default": "reference"},
                    "source":  {"type": "string", "description": "Source (e.g., ai-learned, user-uploaded, manual).", "default": "ai-learned"},
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
                    "query":       {"type": "string",  "description": "Search keyword or phrase."},
                    "category":    {"type": "string",  "description": "Optional category filter."},
                    "max_results": {"type": "integer", "description": "Max entries to return (default 20).", "default": 20},
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
                    "entry_id": {"type": "string", "description": "KB entry ID."},
                    "title":    {"type": "string", "description": "New title (optional)."},
                    "content":  {"type": "string", "description": "New content (optional)."},
                    "tags":     {"type": "array",  "items": {"type": "string"}, "description": "New tags (optional)."},
                    "category": {"type": "string", "description": "New category (optional)."},
                    "source":   {"type": "string", "description": "New source (optional)."},
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
                    "entry_id": {"type": "string", "description": "KB entry ID."},
                    "confirm":  {"type": "boolean", "description": "Must be true to execute deletion.", "default": False},
                },
                "required": ["entry_id", "confirm"],
            },
        ),

        types.Tool(
            name="kb_index",
            description="Get a lightweight index of all knowledge base entries (titles and metadata, no full content). Use to browse available knowledge without loading everything.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Optional category filter."},
                    "limit":    {"type": "integer", "description": "Maximum entries to list (default 100).", "default": 100},
                },
                "required": [],
            },
        ),

        types.Tool(
            name="kb_import",
            description="Bulk-import a large text document into the knowledge base. The text is automatically split into paragraphs and saved as separate entries. Use when the user pastes documentation, notes, or any large reference material.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text":     {"type": "string", "description": "The full text to import."},
                    "title":    {"type": "string", "description": "Base title for generated entries.", "default": "Imported Document"},
                    "category": {"type": "string", "description": "Category for all imported entries.", "default": "reference"},
                    "source":   {"type": "string", "description": "Source for all imported entries.", "default": "user-uploaded"},
                },
                "required": ["text"],
            },
        ),

        # ── Session (Short-Term Memory) ───────────────────────────────────────

        types.Tool(
            name="session_start",
            description="Start a new short-term memory session. Call this at the beginning of every conversation to enable in-session context tracking and pending save queuing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_type": {"type": "string", "description": "Type of task (e.g., coding, planning, research).", "default": "general"},
                },
                "required": [],
            },
        ),

        types.Tool(
            name="session_update",
            description="Update a key-value pair in the active session's context.",
            inputSchema={
                "type": "object",
                "properties": {
                    "key":   {"type": "string", "description": "Context key."},
                    "value": {"type": "string", "description": "Context value."},
                },
                "required": ["key", "value"],
            },
        ),

        types.Tool(
            name="session_event",
            description="Log a notable event to the session timeline (e.g. memory trigger, user correction).",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {"type": "string", "description": "Type of event (e.g., memory_trigger, user_correction, error)."},
                    "details":    {"type": "string", "description": "Event details."},
                },
                "required": ["event_type", "details"],
            },
        ),

        types.Tool(
            name="session_queue",
            description="Queue an item for pending save to LTM or KB. Use when AI detects memory-worthy content mid-conversation and wants to save it after user confirmation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {"type": "string", "description": "Type: 'ltm' or 'kb'."},
                    "content":   {"type": "string", "description": "Content to save."},
                    "metadata":  {"type": "object", "description": "Optional metadata (e.g., category, tags).", "default": {}},
                },
                "required": ["item_type", "content"],
            },
        ),

        types.Tool(
            name="session_pending",
            description="Get all items queued for saving in the current session.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),

        types.Tool(
            name="session_end",
            description="End the current session and get a summary. Call at conversation end to flush pending saves and clean up STM. Set auto_flush=true to automatically write all pending_saves to LTM/KB. Returns a summary with all pending_saves the AI should process.",
            inputSchema={
                "type": "object",
                "properties": {
                    "auto_flush": {"type": "boolean", "description": "If true, automatically write pending saves to LTM/KB.", "default": False},
                },
                "required": [],
            },
        ),

        # ── Status ────────────────────────────────────────────────────────────

        types.Tool(
            name="memory_status",
            description="Get overall memory system status: entry counts, active sessions, system health. Use for diagnostics or when user asks about memory.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),

        # ── Trigger Analysis ──────────────────────────────────────────────────

        types.Tool(
            name="trigger_analyze",
            description=(
                "分析文本，识别值得保存的记忆内容。返回建议列表（不自动写入）。\n"
                "Analyze text (or a session's events) for memory-worthy content. "
                "Returns a list of save suggestions with confidence scores — does NOT automatically save anything. "
                "Call this at conversation end or when unsure what to save. Human/AI confirms before actual saving."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to analyze for memory-worthy content."},
                },
                "required": ["text"],
            },
        ),

    ]


# ─────────────────────────────────────────────────────────────────────────────
# Tool Handlers (与原版完全一致，但底层使用 WAL 增强版)
# ─────────────────────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    try:
        # ── Long-Term Memory ──────────────────────────────────────────────────

        if name == "memory_save":
            entry = _ltm.save(
                content=arguments["content"],
                category=arguments.get("category", "other"),
                source=arguments.get("source", "ai-detected"),
                tags=arguments.get("tags", []),
                passphrase=arguments.get("passphrase"),
            )
            return _ok(_entry_dict(entry))

        elif name == "memory_recall":
            results = _ltm.search(
                query=arguments["query"],
                category=arguments.get("category"),
                max_results=arguments.get("max_results", 20),
            )
            return _ok([_entry_dict(e) for e in results])

        elif name == "memory_get":
            entry = _ltm.get(arguments["entry_id"])
            if entry is None:
                return _err(f"Entry '{arguments['entry_id']}' not found.")
            return _ok(_entry_dict(entry))

        elif name == "memory_update":
            entry = _ltm.update(
                entry_id=arguments["entry_id"],
                content=arguments.get("content"),
                tags=arguments.get("tags"),
                category=arguments.get("category"),
            )
            return _ok(_entry_dict(entry))

        elif name == "memory_delete":
            success = _ltm.delete(
                entry_id=arguments["entry_id"],
                confirm=arguments["confirm"],
            )
            if not success:
                return _err(f"Entry '{arguments['entry_id']}' not found or already deleted.")
            return _ok({"deleted": arguments["entry_id"]})

        elif name == "memory_profile":
            profile = _ltm.load_profile()
            return _ok(profile)

        elif name == "memory_list":
            entries = _ltm.list_all(
                category=arguments.get("category"),
                limit=arguments.get("limit", 100),
            )
            return _ok([_entry_dict(e) for e in entries])

        # ── Knowledge Base ────────────────────────────────────────────────────

        elif name == "kb_add":
            entry = _kb.add(
                title=arguments["title"],
                content=arguments["content"],
                tags=arguments.get("tags", []),
                category=arguments.get("category", "reference"),
                source=arguments.get("source", "ai-learned"),
            )
            return _ok(_entry_dict(entry))

        elif name == "kb_search":
            results = _kb.search(
                query=arguments["query"],
                category=arguments.get("category"),
                max_results=arguments.get("max_results", 20),
            )
            return _ok([_entry_dict(e) for e in results])

        elif name == "kb_update":
            entry = _kb.update(
                entry_id=arguments["entry_id"],
                title=arguments.get("title"),
                content=arguments.get("content"),
                tags=arguments.get("tags"),
                category=arguments.get("category"),
                source=arguments.get("source"),
            )
            return _ok(_entry_dict(entry))

        elif name == "kb_delete":
            success = _kb.delete(
                entry_id=arguments["entry_id"],
                confirm=arguments["confirm"],
            )
            if not success:
                return _err(f"KB entry '{arguments['entry_id']}' not found or already deleted.")
            return _ok({"deleted": arguments["entry_id"]})

        elif name == "kb_index":
            index = _kb.index(
                category=arguments.get("category"),
                limit=arguments.get("limit", 100),
            )
            return _ok(index)

        elif name == "kb_import":
            imported = _kb.bulk_import(
                text=arguments["text"],
                base_title=arguments.get("title", "Imported Document"),
                category=arguments.get("category", "reference"),
                source=arguments.get("source", "user-uploaded"),
            )
            return _ok({"imported_count": len(imported), "entries": [_entry_dict(e) for e in imported]})

        # ── Session ───────────────────────────────────────────────────────────

        elif name == "session_start":
            session_id = _stm.start_session(task_type=arguments.get("task_type", "general"))
            return _ok({"session_id": session_id})

        elif name == "session_update":
            _stm.update_context(key=arguments["key"], value=arguments["value"])
            return _ok({"updated": arguments["key"]})

        elif name == "session_event":
            _stm.log_event(
                event_type=arguments["event_type"],
                details=arguments["details"],
            )
            return _ok({"logged": arguments["event_type"]})

        elif name == "session_queue":
            pending_id = _stm.queue_pending(
                item_type=arguments["item_type"],
                content=arguments["content"],
                metadata=arguments.get("metadata", {}),
            )
            return _ok({"pending_id": pending_id})

        elif name == "session_pending":
            pending = _stm.get_pending()
            return _ok(pending)

        elif name == "session_end":
            summary = _stm.end_session(auto_flush=arguments.get("auto_flush", False))
            return _ok(summary)

        # ── Status ────────────────────────────────────────────────────────────

        elif name == "memory_status":
            ltm_counts = {cat: len(_ltm._load_shard(cat)) for cat in ["profile", "preference", "project", "decision", "habit", "credential", "other"]}
            kb_count = len(_kb.list_all())
            active_sessions = _stm.active_session_count()
            
            # 获取 WAL 统计信息
            wal_stats = _ltm.get_wal_stats() if hasattr(_ltm, 'get_wal_stats') else {"enabled": False}
            
            status = {
                "long_term_memory": {
                    "total_entries": sum(ltm_counts.values()),
                    "by_category": ltm_counts,
                },
                "knowledge_base": {
                    "total_entries": kb_count,
                },
                "sessions": {
                    "active": active_sessions,
                },
                "write_ahead_log": wal_stats,
                "system": {
                    "memory_dir": str(MEMORY_DIR),
                    "wal_enabled": WAL_ENABLED,
                    "version": "1.4.1 (WAL-enhanced)",
                }
            }
            return _ok(status)

        # ── Trigger Analysis ──────────────────────────────────────────────────

        elif name == "trigger_analyze":
            suggestions = _trig.analyze(arguments["text"])
            return _ok(suggestions)

        # ── Unknown tool ──────────────────────────────────────────────────────

        else:
            return _err(f"Unknown tool '{name}'.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        return _err(f"Tool '{name}' failed: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Server Entry Point
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="AI Memory System MCP Server (WAL-enhanced)")
    parser.add_argument("--sse", action="store_true", help="Run in SSE mode (HTTP)")
    parser.add_argument("--port", type=int, default=8766, help="Port for SSE mode (default: 8766)")
    args = parser.parse_args()

    if args.sse:
        # SSE mode (HTTP)
        import uvicorn
        from mcp.server.sse import SseServerTransport
        
        transport = SseServerTransport(args.port)
        print(f"🚀 Starting SSE server on http://localhost:{args.port}")
        await server.run(transport, raise_exceptions=True)
    else:
        # stdio mode (default for WorkBuddy)
        from mcp.server.stdio import stdio_server
        
        print("🚀 Starting stdio server (ready for WorkBuddy)")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                raise_exceptions=True,
            )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
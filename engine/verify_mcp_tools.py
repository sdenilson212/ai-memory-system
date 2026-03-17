"""
verify_mcp_tools.py -- Test all MCP tool handlers end-to-end
Run: python verify_mcp_tools.py
"""
import sys, asyncio
sys.path.insert(0, r'C:/Users/sdenilson/WorkBuddy/Claw/output/ai-memory-system/engine')

from mcp_server import call_tool

PASS = "[PASS]"
FAIL = "[FAIL]"

async def run_tests():
    results = []

    async def check(label, coro, expect_key=None, expect_val=None, expect_no_error=True):
        import json
        try:
            out = await coro
            text = out[0].text
            data = json.loads(text)
            if expect_no_error and "error" in data:
                results.append((FAIL, label, "Got error: " + data["error"]))
                return data
            if expect_key and expect_key not in data:
                results.append((FAIL, label, f"Missing key '{expect_key}' in: {data}"))
                return data
            if expect_val is not None and data.get(expect_key) != expect_val:
                results.append((FAIL, label, f"Expected {expect_key}={expect_val!r}, got {data.get(expect_key)!r}"))
                return data
            results.append((PASS, label, ""))
            return data
        except Exception as e:
            results.append((FAIL, label, str(e)))
            return {}

    # ── memory_save ──
    saved = await check(
        "memory_save: basic",
        call_tool("memory_save", {"content": "User prefers dark mode", "category": "preference", "tags": ["ui"]}),
        expect_key="status", expect_val="saved"
    )
    entry_id = saved.get("entry_id", "")

    # ── memory_recall ──
    await check(
        "memory_recall: keyword search",
        call_tool("memory_recall", {"query": "dark mode"}),
    )

    # ── memory_get ──
    if entry_id:
        await check(
            "memory_get: by ID",
            call_tool("memory_get", {"entry_id": entry_id}),
            expect_key="id"
        )

    # ── memory_update ──
    if entry_id:
        await check(
            "memory_update: change tags",
            call_tool("memory_update", {"entry_id": entry_id, "tags": ["ui", "theme"]}),
            expect_key="status", expect_val="updated"
        )

    # ── memory_profile ──
    await check(
        "memory_profile",
        call_tool("memory_profile", {}),
        expect_key="total_entries"
    )

    # ── memory_list ──
    await check(
        "memory_list",
        call_tool("memory_list", {"category": "preference", "limit": 10}),
    )

    # ── memory_delete (no confirm = error expected) ──
    if entry_id:
        import json
        out = await call_tool("memory_delete", {"entry_id": entry_id, "confirm": False})
        data = json.loads(out[0].text)
        if "error" in data:
            results.append((PASS, "memory_delete: no-confirm raises error", ""))
        else:
            results.append((FAIL, "memory_delete: no-confirm should return error", str(data)))

    # ── memory_delete (confirmed) ──
    if entry_id:
        await check(
            "memory_delete: confirmed",
            call_tool("memory_delete", {"entry_id": entry_id, "confirm": True}),
            expect_key="status"
        )

    # ── kb_add ──
    kb_added = await check(
        "kb_add",
        call_tool("kb_add", {
            "title": "FastAPI Tips",
            "content": "Use dependency injection for clean code",
            "category": "technical",
            "tags": ["python", "fastapi"]
        }),
        expect_key="status", expect_val="added"
    )
    kb_id = kb_added.get("entry_id", "")

    # ── kb_search ──
    await check(
        "kb_search",
        call_tool("kb_search", {"query": "fastapi"}),
    )

    # ── kb_index ──
    await check(
        "kb_index",
        call_tool("kb_index", {}),
    )

    # ── kb_import ──
    await check(
        "kb_import",
        call_tool("kb_import", {
            "text": "Python is great for AI.\n\nFastAPI is a modern web framework.\n\nChromaDB is a vector database.",
            "category": "technical"
        }),
        expect_key="status", expect_val="imported"
    )

    # ── kb_update ──
    if kb_id:
        await check(
            "kb_update",
            call_tool("kb_update", {"entry_id": kb_id, "tags": ["python", "fastapi", "updated"]}),
            expect_key="status", expect_val="updated"
        )

    # ── kb_delete ──
    if kb_id:
        await check(
            "kb_delete: confirmed",
            call_tool("kb_delete", {"entry_id": kb_id, "confirm": True}),
            expect_key="status"
        )

    # ── session_start ──
    sess = await check(
        "session_start",
        call_tool("session_start", {"task_type": "coding"}),
        expect_key="session_id"
    )
    sid = sess.get("session_id", "")

    # ── session_update ──
    if sid:
        await check(
            "session_update",
            call_tool("session_update", {"session_id": sid, "key": "project", "value": "memory-engine"}),
            expect_key="status", expect_val="updated"
        )

    # ── session_event ──
    if sid:
        await check(
            "session_event",
            call_tool("session_event", {"session_id": sid, "event_type": "memory_trigger", "content": "User mentioned dark mode"}),
            expect_key="status", expect_val="logged"
        )

    # ── session_queue ──
    if sid:
        await check(
            "session_queue",
            call_tool("session_queue", {"session_id": sid, "content": "Remember: user uses dark mode", "category": "preference"}),
            expect_key="status", expect_val="queued"
        )

    # ── session_pending ──
    if sid:
        await check(
            "session_pending",
            call_tool("session_pending", {"session_id": sid}),
            expect_key="count"
        )

    # ── session_end ──
    if sid:
        await check(
            "session_end",
            call_tool("session_end", {"session_id": sid}),
            expect_key="session_id"
        )

    # ── memory_status ──
    await check(
        "memory_status",
        call_tool("memory_status", {}),
        expect_key="system"
    )

    # ── trigger_analyze ──
    await check(
        "trigger_analyze: text",
        call_tool("trigger_analyze", {"text": "I prefer dark mode and usually code at night"}),
        expect_key="suggestions"
    )

    # ── Print results ──
    print()
    passed = sum(1 for r in results if r[0] == PASS)
    total  = len(results)
    for status, label, detail in results:
        suffix = f" -- {detail}" if detail else ""
        print(f"{status} {label}{suffix}")

    print()
    if passed == total:
        print(f"ALL {total} MCP TOOL TESTS PASSED")
    else:
        print(f"{passed}/{total} passed -- {total - passed} FAILED")


asyncio.run(run_tests())

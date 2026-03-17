"""
综合测试：启动服务器 + 等待就绪 + 跑 API 测试 + 打印结果
"""
import sys
import os
import subprocess
import time
import json
import urllib.request
import urllib.error
import threading

ENGINE_DIR = r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine'
BASE = "http://127.0.0.1:8765"
PASS_S = "[PASS]"
FAIL_S = "[FAIL]"

# ── 1. Start server ───────────────────────────────────────────────────────────
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
server = subprocess.Popen(
    [sys.executable, "main.py"],
    cwd=ENGINE_DIR,
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# ── 2. Wait for server to be ready ────────────────────────────────────────────
def wait_ready(timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(BASE + "/health", timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False

print("Waiting for server...")
ready = wait_ready(15)
if not ready:
    server.terminate()
    out, err = server.communicate(timeout=5)
    print("Server failed to start!")
    print("STDOUT:", out.decode("utf-8", errors="replace")[:1000])
    print("STDERR:", err.decode("utf-8", errors="replace")[:1000])
    sys.exit(1)

print(f"Server is up at {BASE}\n")

# ── 3. API Tests ──────────────────────────────────────────────────────────────
results = []

def get(path):
    try:
        r = urllib.request.urlopen(BASE + path, timeout=8)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def post(path, data):
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            BASE + path, data=body,
            headers={"Content-Type": "application/json"}
        )
        r = urllib.request.urlopen(req, timeout=8)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return {"error": json.loads(e.read()).get("detail", str(e))}
        except Exception:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def check(label, result, expect_key=None, expect_val=None):
    if "error" in result and expect_key != "error":
        results.append((FAIL_S, label, str(result["error"])))
        return result
    if expect_key and expect_key not in result:
        results.append((FAIL_S, label, f"missing key '{expect_key}': {list(result.keys())}"))
        return result
    if expect_val is not None and result.get(expect_key) != expect_val:
        results.append((FAIL_S, label, f"expected {expect_val!r}, got {result.get(expect_key)!r}"))
        return result
    results.append((PASS_S, label, ""))
    return result

# Health
check("GET /health", get("/health"), "status", "ok")

# Memory save
r = check("POST /memory/save", post("/memory/save", {
    "content": "User prefers dark mode UI",
    "category": "preference",
    "tags": ["ui", "theme"]
}), "success", True)
entry_id = r.get("entry_id", "")

# Memory recall (GET with params)
check("GET /memory/recall", get("/memory/recall?query=dark+mode&limit=5"), "count")

# Memory get
if entry_id:
    check("GET /memory/{id}", get(f"/memory/{entry_id}"), "id")

# Memory profile
check("GET /memory/profile", get("/memory/profile"), "total_entries")

# Memory list
check("GET /memory/list", get("/memory/list?category=preference&limit=5"), "count")

# Memory status (via MCP, not REST — use health instead)
check("GET /health (system check)", get("/health"), "status")

# KB add
r = check("POST /kb/add", post("/kb/add", {
    "title": "FastAPI Best Practices",
    "content": "Use dependency injection and Pydantic models",
    "category": "technical",
    "tags": ["python", "fastapi"]
}), "success", True)
kb_id = r.get("entry_id", "")

# KB search (GET)
check("GET /kb/search", get("/kb/search?query=fastapi&limit=5"))

# KB index
check("GET /kb/index", get("/kb/index"))

# KB import
check("POST /kb/import", post("/kb/import", {
    "text": "Python is a programming language.\n\nFastAPI is modern and fast.",
    "category": "technical"
}), "success", True)

# Session start
r = check("POST /session/start", post("/session/start", {"task_type": "api_test"}), "session_id")
sid = r.get("session_id", "")

# Session context update
if sid:
    check("POST /session/{id}/context", post(f"/session/{sid}/context", {
        "key": "project", "value": "memory-engine"
    }), "success", True)

# Session event
if sid:
    check("POST /session/{id}/event", post(f"/session/{sid}/event", {
        "event_type": "test_event",
        "content": "API test running"
    }), "success", True)

# Session queue
if sid:
    check("POST /session/{id}/queue", post(f"/session/{sid}/queue", {
        "content": "Remember: test was successful",
        "category": "test"
    }), "success", True)

# Session pending
if sid:
    check("GET /session/{id}/pending", get(f"/session/{sid}/pending"), "pending_count")

# Session suggestions (trigger_analyze)
if sid:
    check("GET /session/{id}/suggestions", get(f"/session/{sid}/suggestions"), "session_id")

# Analyze text
check("POST /session/analyze", post("/session/analyze", {
    "text": "I prefer dark mode and usually code late at night"
}), "suggestions")

# Session status
if sid:
    check("GET /session/{id}/status", get(f"/session/{sid}/status"), "session_id")

# Session end
if sid:
    check("POST /session/{id}/end", post(f"/session/{sid}/end", {}), "success", True)

# ── 4. Print results ──────────────────────────────────────────────────────────
print()
passed = sum(1 for r in results if r[0] == PASS_S)
total = len(results)
for status, label, detail in results:
    suffix = f"  -- {detail}" if detail else ""
    print(f"  {status} {label}{suffix}")

print()
if passed == total:
    print(f"ALL {total} API TESTS PASSED")
else:
    print(f"{passed}/{total} passed  --  {total - passed} FAILED")

# ── 5. Cleanup ────────────────────────────────────────────────────────────────
server.terminate()

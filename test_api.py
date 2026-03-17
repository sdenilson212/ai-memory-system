import urllib.request
import json
import sys

BASE = "http://localhost:8765"

def get(path):
    try:
        r = urllib.request.urlopen(BASE + path, timeout=5)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def post(path, data):
    try:
        body = json.dumps(data).encode()
        req = urllib.request.Request(BASE + path, data=body, headers={"Content-Type": "application/json"})
        r = urllib.request.urlopen(req, timeout=5)
        return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

PASS = "[PASS]"
FAIL = "[FAIL]"
results = []

def check(label, result, expect_key=None):
    if "error" in result:
        results.append((FAIL, label, result["error"]))
    elif expect_key and expect_key not in result:
        results.append((FAIL, label, f"missing key '{expect_key}': {result}"))
    else:
        results.append((PASS, label, ""))

# 1. Health check
r = get("/health")
check("GET /health", r, "status")

# 2. Memory status
r = get("/memory/status")
check("GET /memory/status", r, "system")

# 3. Save a memory
r = post("/memory/save", {"content": "API test entry", "category": "test", "tags": ["api"]})
check("POST /memory/save", r, "status")
entry_id = r.get("entry_id", "")

# 4. Recall
r = post("/memory/recall", {"query": "API test", "limit": 5})
check("POST /memory/recall", r)

# 5. Memory profile
r = get("/memory/profile")
check("GET /memory/profile", r, "total_entries")

# 6. KB search
r = post("/kb/search", {"query": "python", "limit": 5})
check("POST /kb/search", r)

# 7. Session start
r = post("/session/start", {"task_type": "testing"})
check("POST /session/start", r, "session_id")
sid = r.get("session_id", "")

# 8. Session suggestions (trigger)
if sid:
    r = get(f"/session/{sid}/suggestions")
    check(f"GET /session/{sid}/suggestions", r)

# 9. Analyze text
r = post("/session/analyze", {"text": "I prefer dark mode and usually code late at night"})
check("POST /session/analyze", r, "suggestions")

# 10. Session end
if sid:
    r = post(f"/session/{sid}/end", {})
    check(f"POST /session/{sid}/end", r, "session_id")

# Print results
print()
passed = sum(1 for r in results if r[0] == PASS)
total = len(results)
for status, label, detail in results:
    suffix = f" -- {detail}" if detail else ""
    print(f"{status} {label}{suffix}")

print()
if passed == total:
    print(f"ALL {total} API TESTS PASSED")
else:
    print(f"{passed}/{total} passed -- {total - passed} FAILED")

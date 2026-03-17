import sys
sys.path.insert(0, r'C:/Users/sdenilson/WorkBuddy/Claw/output/ai-memory-system/engine')

try:
    from mcp_server import server
    print("[OK] mcp_server import OK")
    print("[OK] server name:", server.name)
except ImportError as e:
    print("[FAIL] ImportError:", e)
except Exception as e:
    print("[FAIL]", type(e).__name__, e)

import sys
sys.path.insert(0, r'C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine')

# Test all core imports
try:
    from config import MEMORY_DIR, SECURE_DIR
    print("config: OK, MEMORY_DIR =", MEMORY_DIR)
except Exception as e:
    print("config FAIL:", e)

try:
    from core.ltm import LTMManager
    print("core.ltm: OK")
except Exception as e:
    print("core.ltm FAIL:", e)

try:
    from core.kb import KBManager
    print("core.kb: OK")
except Exception as e:
    print("core.kb FAIL:", e)

try:
    from core.stm import STMManager
    print("core.stm: OK")
except Exception as e:
    print("core.stm FAIL:", e)

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    print("mcp server libs: OK")
except Exception as e:
    print("mcp libs FAIL:", e)

print("All checks done.")

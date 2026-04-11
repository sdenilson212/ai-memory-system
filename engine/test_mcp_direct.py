"""Test MCP server connectivity directly."""
import sys
import os

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add engine directory to path
engine_dir = r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine"
sys.path.insert(0, engine_dir)

os.chdir(engine_dir)

# Test imports
print("=" * 60)
print("TESTING MCP SERVER IMPORTS")
print("=" * 60)

try:
    print("\n[1/5] Testing config import...")
    from config import MEMORY_DIR, SECURE_DIR
    print(f"  ✅ OK - MEMORY_DIR: {MEMORY_DIR}")
    print(f"  ✅ OK - SECURE_DIR: {SECURE_DIR}")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    sys.exit(1)

try:
    print("\n[2/5] Testing core modules...")
    from core.ltm import LTMManager
    from core.kb import KBManager
    from core.stm import STMManager
    from core.trigger import TriggerEngine
    print("  ✅ OK - All core modules imported")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    sys.exit(1)

try:
    print("\n[3/5] Testing security modules...")
    from security.detector import SensitiveDetector
    from security.encryptor import Encryptor
    print("  ✅ OK - All security modules imported")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    sys.exit(1)

try:
    print("\n[4/5] Testing MCP imports...")
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    print("  ✅ OK - All MCP modules imported")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[5/5] Testing mcp_server module...")
    import mcp_server
    print(f"  ✅ OK - mcp_server module loaded")
    print(f"  ✅ OK - Server name: {mcp_server.server.name}")
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
print("\nMCP server should be working correctly.")
print("If it times out in WorkBuddy, the issue may be:")
print("  1. WorkBuddy not reading the correct mcp.json")
print("  2. WorkBuddy needs to be restarted")
print("  3. Path issues in the configuration")

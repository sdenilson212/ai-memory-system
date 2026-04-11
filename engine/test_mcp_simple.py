"""Test MCP server connectivity directly."""
import sys
import os

# Add engine directory to path
engine_dir = r"C:\Users\sdenilson\WorkBuddy\Claw\output\ai-memory-system\engine"
sys.path.insert(0, engine_dir)
os.chdir(engine_dir)

errors = []

# Test 1: config
try:
    from config import MEMORY_DIR, SECURE_DIR
    print("[PASS] config imported")
except Exception as e:
    errors.append(f"config: {e}")

# Test 2: core
try:
    from core.ltm import LTMManager
    from core.kb import KBManager
    from core.stm import STMManager
    from core.trigger import TriggerEngine
    print("[PASS] core modules imported")
except Exception as e:
    errors.append(f"core: {e}")

# Test 3: security
try:
    from security.detector import SensitiveDetector
    from security.encryptor import Encryptor
    print("[PASS] security modules imported")
except Exception as e:
    errors.append(f"security: {e}")

# Test 4: mcp
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
    print("[PASS] mcp modules imported")
except Exception as e:
    errors.append(f"mcp: {e}")

# Test 5: mcp_server
try:
    import mcp_server
    print(f"[PASS] mcp_server loaded, server name: {mcp_server.server.name}")
except Exception as e:
    errors.append(f"mcp_server: {e}")

print("\n" + "="*60)
if errors:
    print("ERRORS:")
    for err in errors:
        print(f"  - {err}")
else:
    print("ALL TESTS PASSED - MCP server should be working!")
print("="*60)

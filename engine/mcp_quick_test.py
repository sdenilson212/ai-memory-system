"""
Quick MCP Server Test
=====================
Run this to verify MCP server is working correctly.
"""

import sys
import os

# Set up paths
engine_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, engine_dir)
os.chdir(engine_dir)

print("="*60)
print("QUICK MCP SERVER TEST")
print("="*60)

# Test 1: Import all modules
print("\n[TEST 1] Import modules...")
try:
    from config import MEMORY_DIR
    from core.ltm import LTMManager
    from core.kb import KBManager
    from core.stm import STMManager
    from security.detector import SensitiveDetector
    from security.encryptor import Encryptor
    from mcp.server import Server
    import mcp_server
    print("PASS: All modules imported")
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)

# Test 2: Check server object
print("\n[TEST 2] Check server object...")
try:
    server = mcp_server.server
    print(f"PASS: Server name = {server.name}")
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)

# Test 3: Test LTM
print("\n[TEST 3] Test LTM (Long-Term Memory)...")
try:
    from config import MEMORY_DIR
    from core.ltm import LTMManager
    from security.detector import SensitiveDetector
    from security.encryptor import Encryptor

    enc = Encryptor(os.path.join(os.path.dirname(MEMORY_DIR), "secure"))
    det = SensitiveDetector()
    ltm = LTMManager(MEMORY_DIR, encryptor=enc, detector=det)

    # Try to save a test entry
    test_entry = ltm.save(
        content="Test entry from quick test",
        category="other",
        source="ai-detected"
    )
    print(f"PASS: Saved test entry (ID: {test_entry.id[:8]}...)")

    # Try to search
    results = ltm.search(query="test", max_results=5)
    print(f"PASS: Found {len(results)} entries")

except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test KB
print("\n[TEST 4] Test KB (Knowledge Base)...")
try:
    kb = KBManager(MEMORY_DIR)

    # Try to add a test entry
    test_entry = kb.add(
        title="Quick Test",
        content="Test knowledge entry",
        category="reference"
    )
    print(f"PASS: Added test KB entry (ID: {test_entry.id[:8]}...)")

    # Try to search
    results = kb.search(query="test", top_k=5)
    print(f"PASS: Found {len(results)} KB entries")

except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test STM
print("\n[TEST 5] Test STM (Session Management)...")
try:
    stm = STMManager()

    # Try to start a session
    session = stm.start_session(task_type="test")
    print(f"PASS: Started session (ID: {session.session_id[:8]}...)")

    # Try to update context
    stm.update_context(session.session_id, "test_key", "test_value")
    print("PASS: Updated session context")

    # Try to end session
    summary = stm.end_session(session.session_id)
    print(f"PASS: Ended session")

except Exception as e:
    print(f"FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("ALL TESTS PASSED!")
print("="*60)
print("\nMCP server is working correctly.")
print("If WorkBuddy times out, restart WorkBuddy application.")
print("="*60)

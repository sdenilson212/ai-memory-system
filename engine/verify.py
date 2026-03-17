import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from security.detector import SensitiveDetector
from security.encryptor import Encryptor
from core.ltm import LTMManager
from core.kb import KBManager
from core.stm import STMManager
from pathlib import Path
import tempfile

ok = "[OK]"
fail = "[FAIL]"

print("=== AI Memory Engine - Verification ===")
print(ok + " All modules imported")

# Test detector
detector = SensitiveDetector()
result = detector.scan("My API key is sk-abc123XYZabcABC456789")
assert result.is_sensitive, "Should detect API key"
assert "[API_KEY" in result.redacted_text
print(ok + " SensitiveDetector: API key detection")

result2 = detector.scan("Hello, I am learning Python today")
assert not result2.is_sensitive
print(ok + " SensitiveDetector: safe text passes")

# Test encryptor
with tempfile.TemporaryDirectory() as tmpdir:
    enc = Encryptor(Path(tmpdir))
    entry_id = enc.encrypt("test_key", "super_secret_value", "my-passphrase", "api_key")
    assert entry_id

    plaintext = enc.decrypt(entry_id, "my-passphrase")
    assert plaintext == "super_secret_value"
    print(ok + " Encryptor: encrypt/decrypt roundtrip")

    keys = enc.list_keys()
    assert len(keys) == 1
    assert "ciphertext_hex" not in keys[0]
    print(ok + " Encryptor: list_keys does not expose ciphertext")

    deleted = enc.delete(entry_id, "my-passphrase")
    assert deleted
    print(ok + " Encryptor: delete works")

# Test LTM
with tempfile.TemporaryDirectory() as tmpdir:
    ltm = LTMManager(Path(tmpdir))
    entry = ltm.save("I prefer Python over Java", category="preference", source="user-explicit", tags=["coding"])
    assert entry.id
    print(ok + " LTMManager: save")

    found = ltm.get(entry.id)
    assert found.content == "I prefer Python over Java"
    print(ok + " LTMManager: get")

    results = ltm.search("Python")
    assert len(results) == 1
    print(ok + " LTMManager: search")

    profile = ltm.load_profile()
    assert profile["total_entries"] == 1
    print(ok + " LTMManager: load_profile")

# Test KB
with tempfile.TemporaryDirectory() as tmpdir:
    kb = KBManager(Path(tmpdir))
    entry = kb.add("FastAPI Tips", "Use dependency injection for DB sessions", category="technical", tags=["fastapi"])
    assert entry.id
    print(ok + " KBManager: add")

    results = kb.search("fastapi")
    assert len(results) == 1
    print(ok + " KBManager: search")

    index = kb.get_index()
    assert len(index) == 1
    assert "content" not in index[0]
    print(ok + " KBManager: get_index (no content leak)")

    imported = kb.import_text(
        "First paragraph of text here with enough content to be imported.\n\n"
        "Second paragraph also has enough content for the import testing function.",
        category="domain"
    )
    assert len(imported) >= 1
    print(ok + " KBManager: import_text ({} chunks)".format(len(imported)))

# Test STM
stm = STMManager()
session = stm.start_session("coding")
sid = session.session_id
assert sid
print(ok + " STMManager: start_session")

stm.update_context(sid, "current_project", "memory-engine")
s = stm.get_session(sid)
assert s.context["current_project"] == "memory-engine"
print(ok + " STMManager: update_context")

stm.add_event(sid, "memory_trigger", "User mentioned project name")
stm.queue_save(sid, {"content": "Project: memory-engine", "category": "project", "source": "ai-detected"})

pending = stm.get_pending_saves(sid)
assert len(pending) == 1
print(ok + " STMManager: queue_save + get_pending_saves")

summary = stm.end_session(sid)
assert summary["event_count"] == 1
assert len(summary["pending_saves"]) == 1
assert stm.get_session(sid) is None
print(ok + " STMManager: end_session clears memory")

print("")
print("=" * 40)
print("ALL TESTS PASSED - Engine is ready!")
print("=" * 40)

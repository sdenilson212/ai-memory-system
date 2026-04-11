"""
test_search_fix_v2.py - verify search() + weight integration (file-output version)
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

RESULT_FILE = Path(__file__).parent.parent / "test_search_result_v2.txt"

results_log = []

def log(msg):
    results_log.append(msg)

from core.ltm import LTMManager
from core.weight import MemoryWeight

def test_search_returns_results():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        ltm = LTMManager(d)
        ltm.save("I prefer Python programming", "preference")
        ltm.save("I enjoy running in the morning", "habit")
        ltm.save("My project is AI memory system", "project")

        results = ltm.search("Python")
        assert len(results) > 0, f"search() returned no results! Got: {results}"
        assert any("Python" in r.content for r in results), "Expected Python in results"
        log("[PASS] test_search_returns_results")

def test_search_empty_query():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        ltm = LTMManager(d)
        ltm.save("Entry 1", "preference")
        ltm.save("Entry 2", "habit")

        results = ltm.search("")
        assert isinstance(results, list), "search('') should return a list"
        log("[PASS] test_search_empty_query")

def test_weight_affects_ranking():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        ltm = LTMManager(d)

        e_low = ltm.save("memory test entry normal", "preference")
        e_high = ltm.save("memory test entry important", "preference")

        mw = MemoryWeight(d)
        mw.set_weight(e_low.id, 1)   # LOW
        mw.set_weight(e_high.id, 5)  # CORE

        results = ltm.search("memory test entry", use_weight=True)
        assert len(results) >= 2, f"Expected >=2 results, got {len(results)}"
        result_ids = [r.id for r in results]
        assert e_high.id in result_ids, "High-weight entry missing from results"

        if e_low.id in result_ids:
            high_rank = result_ids.index(e_high.id)
            low_rank = result_ids.index(e_low.id)
            assert high_rank <= low_rank, (
                f"High-weight entry (rank {high_rank}) should be before low-weight (rank {low_rank})"
            )
        log("[PASS] test_weight_affects_ranking")

def test_weight_disabled():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        ltm = LTMManager(d)
        ltm.save("test content alpha", "preference")
        ltm.save("test content beta", "preference")
        results = ltm.search("test content", use_weight=False)
        assert isinstance(results, list)
        log("[PASS] test_weight_disabled")

def test_recall_alias():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        ltm = LTMManager(d)
        ltm.save("running is good for health", "habit")
        results = ltm.recall("running")
        assert len(results) > 0, "recall() returned no results"
        log("[PASS] test_recall_alias")

tests = [
    test_search_returns_results,
    test_search_empty_query,
    test_weight_affects_ranking,
    test_weight_disabled,
    test_recall_alias,
]

passed = 0
failed = 0
for t in tests:
    try:
        t()
        passed += 1
    except Exception as e:
        log(f"[FAIL] {t.__name__}: {e}")
        import traceback
        log(traceback.format_exc())
        failed += 1

log(f"\nResults: {passed}/{len(tests)} passed, {failed} failed")

RESULT_FILE.write_text("\n".join(results_log), encoding="utf-8")
sys.exit(0 if failed == 0 else 1)

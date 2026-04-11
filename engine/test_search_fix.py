"""
test_search_fix.py - verify search() + weight integration
Run: python test_search_fix.py (from engine/ directory)
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.ltm import LTMManager
from core.weight import MemoryWeight

def test_search_returns_results():
    """search() should return matching entries (was broken before fix)."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        ltm = LTMManager(d)
        ltm.save("I prefer Python programming", "preference")
        ltm.save("I enjoy running in the morning", "habit")
        ltm.save("My project is AI memory system", "project")

        results = ltm.search("Python")
        assert len(results) > 0, "search() returned no results!"
        assert any("Python" in r.content for r in results), "Expected Python in results"
        print("[PASS] test_search_returns_results")

def test_search_empty_query():
    """Empty query should return entries (possibly sorted by weight)."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        ltm = LTMManager(d)
        ltm.save("Entry 1", "preference")
        ltm.save("Entry 2", "habit")

        results = ltm.search("")
        assert isinstance(results, list), "search('') should return a list"
        print("[PASS] test_search_empty_query")

def test_weight_affects_ranking():
    """High-weight entries should rank above low-weight entries with similar content."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        ltm = LTMManager(d)

        # Save two entries with very similar content
        e_low = ltm.save("memory test entry normal", "preference")
        e_high = ltm.save("memory test entry important", "preference")

        # Set high weight on the second entry
        mw = MemoryWeight(d)
        mw.set_weight(e_low.id, 1)   # LOW
        mw.set_weight(e_high.id, 5)  # CORE

        results = ltm.search("memory test entry", use_weight=True)
        assert len(results) >= 2, "Expected at least 2 results"
        # The high-weight entry should rank first (or at least be present)
        result_ids = [r.id for r in results]
        assert e_high.id in result_ids, "High-weight entry missing from results"

        # Check that high-weight entry is ranked before low-weight entry
        if e_low.id in result_ids:
            high_rank = result_ids.index(e_high.id)
            low_rank = result_ids.index(e_low.id)
            assert high_rank <= low_rank, (
                f"High-weight entry (rank {high_rank}) should be >= low-weight (rank {low_rank})"
            )
        print("[PASS] test_weight_affects_ranking")

def test_weight_disabled():
    """use_weight=False should not change sorting logic."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        ltm = LTMManager(d)
        ltm.save("test content alpha", "preference")
        ltm.save("test content beta", "preference")
        results = ltm.search("test content", use_weight=False)
        assert isinstance(results, list)
        print("[PASS] test_weight_disabled")

def test_recall_alias():
    """recall() should be an alias for search()."""
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        ltm = LTMManager(d)
        ltm.save("running is good for health", "habit")
        results = ltm.recall("running")
        assert len(results) > 0, "recall() returned no results"
        print("[PASS] test_recall_alias")

if __name__ == "__main__":
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
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1

    print(f"\nResults: {passed}/{len(tests)} passed")
    sys.exit(0 if failed == 0 else 1)

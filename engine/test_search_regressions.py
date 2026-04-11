import sys
import tempfile
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR))

from core.kb import KBManager, _tokenize as kb_tokenize
from core.ltm import LTMManager, _tokenize as ltm_tokenize



def test_ltm_search_falls_back_when_bm25_scores_non_positive() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ltm = LTMManager(Path(tmpdir))
        entry = ltm.save(
            "I prefer Python over Java",
            category="preference",
            source="user-explicit",
            tags=["coding"],
        )

        results = ltm.search("Python")

        assert any(item.id == entry.id for item in results)



def test_kb_search_falls_back_for_content_only_match() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        kb = KBManager(Path(tmpdir))
        entry = kb.add(
            "Architecture Notes",
            "Use dependency injection for DB sessions",
            category="technical",
            tags=["backend"],
        )

        results = kb.search("dependency", confirmed_only=False)

        assert any(item.id == entry.id for item in results)


def test_ltm_search_keeps_keyword_hits_when_only_subset_has_positive_bm25() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ltm = LTMManager(Path(tmpdir))
        tag_only = ltm.save(
            "Completely unrelated text",
            category="preference",
            source="user-explicit",
            tags=["python"],
        )
        content_match = ltm.save(
            "Python content beta",
            category="preference",
            source="user-explicit",
            tags=["misc"],
        )

        results = ltm.search("Python")
        result_ids = [item.id for item in results]

        assert tag_only.id in result_ids
        assert content_match.id in result_ids


def test_kb_search_keeps_keyword_hits_when_only_subset_has_positive_bm25() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        kb = KBManager(Path(tmpdir))
        title_match = kb.add(
            "Python Guide",
            "general backend notes",
            category="technical",
            tags=["backend"],
        )
        content_match = kb.add(
            "Architecture Notes",
            "python dependency injection notes",
            category="technical",
            tags=["misc"],
        )

        results = kb.search("python", confirmed_only=False)
        result_ids = [item.id for item in results]

        assert title_match.id in result_ids
        assert content_match.id in result_ids


def test_ltm_punctuation_only_query_matches_blank_query_semantics() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ltm = LTMManager(Path(tmpdir))
        ltm.save(
            "Python async tips",
            category="preference",
            source="user-explicit",
            tags=["coding"],
        )
        ltm.save(
            "Packaging notes",
            category="preference",
            source="user-explicit",
            tags=["python"],
        )

        blank_ids = [item.id for item in ltm.search("   ", max_results=1)]
        punct_ids = [item.id for item in ltm.search("---", max_results=1)]

        assert punct_ids == blank_ids


def test_kb_punctuation_only_query_respects_confirmed_filter_like_blank_query() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        kb = KBManager(Path(tmpdir))
        confirmed = kb.add(
            "Confirmed Note",
            "Python dependency note",
            category="technical",
            tags=["python"],
            confirmed=True,
        )
        kb.add(
            "Draft Note",
            "Unconfirmed python note",
            category="technical",
            tags=["draft"],
            confirmed=False,
        )

        blank_ids = [item.id for item in kb.search("   ", confirmed_only=True)]
        punct_ids = [item.id for item in kb.search("---", confirmed_only=True)]

        assert blank_ids == [confirmed.id]
        assert punct_ids == blank_ids



def test_ltm_tokenize_normalizes_fullwidth_and_accented_latin() -> None:
    tokens = ltm_tokenize("Ｐｙｔｈｏｎ résumé")

    assert "python" in tokens
    assert "résumé" in tokens
    assert "resume" in tokens



def test_kb_tokenize_splits_mixed_cjk_and_latin_runs() -> None:
    tokens = kb_tokenize("多语言Search支持")

    assert "search" in tokens
    assert "多" in tokens
    assert "支持" in tokens



def test_ltm_search_matches_fullwidth_english_query() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        ltm = LTMManager(Path(tmpdir))
        entry = ltm.save(
            "Python async tips",
            category="preference",
            source="user-explicit",
            tags=["coding"],
        )

        results = ltm.search("ＰＹＴＨＯＮ")

        assert any(item.id == entry.id for item in results)



def test_kb_search_matches_accent_folded_query() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        kb = KBManager(Path(tmpdir))
        entry = kb.add(
            "Résumé Writing Guide",
            "A concise guide for multilingual CV writing",
            category="reference",
            tags=["career"],
            confirmed=True,
        )

        results = kb.search("resume", confirmed_only=False)

        assert any(item.id == entry.id for item in results)



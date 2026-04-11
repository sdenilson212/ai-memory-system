"""
core/ltm_search.py — Search Engine for LTM
LTM 搜索引擎模块

职责 (Responsibility):
    - 提供 BM25 + 关键词混合搜索
    - 支持权重加成排序
    - Unicode-aware 多语言分词

暴露接口 (Exposes):
    SearchEngine.search(entries, query, max_results, use_weight) -> list[LTMEntry]
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.ltm import LTMEntry


# BM25 is optional — graceful fallback to keyword scoring if not installed
try:
    from rank_bm25 import BM25Okapi as _BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25Okapi = None  # type: ignore
    _BM25_AVAILABLE = False


def _normalize_text(text: str) -> str:
    """Unicode-aware normalization for multilingual search."""
    return unicodedata.normalize("NFKC", text).casefold()


def _strip_diacritics(text: str) -> str:
    """Create an accent-folded alias for Latin-based languages."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _is_cjk_char(char: str) -> bool:
    code = ord(char)
    return (
        0x3400 <= code <= 0x4DBF  # CJK Extension A
        or 0x4E00 <= code <= 0x9FFF  # CJK Unified Ideographs
        or 0x3040 <= code <= 0x309F  # Hiragana
        or 0x30A0 <= code <= 0x30FF  # Katakana
        or 0xAC00 <= code <= 0xD7AF  # Hangul syllables
    )


def _script_runs(part: str) -> list[tuple[str, bool]]:
    runs: list[tuple[str, bool]] = []
    current: list[str] = []
    current_is_cjk: bool | None = None

    for char in part:
        is_cjk = _is_cjk_char(char)
        if current and current_is_cjk != is_cjk:
            runs.append(("".join(current), bool(current_is_cjk)))
            current = [char]
        else:
            current.append(char)
        current_is_cjk = is_cjk

    if current:
        runs.append(("".join(current), bool(current_is_cjk)))
    return runs


def _expand_cjk_run(part: str) -> list[str]:
    tokens = list(part)
    if len(part) > 1:
        tokens.append(part)
        tokens.extend(part[i : i + 2] for i in range(len(part) - 1))
    return tokens


def _append_unique(tokens: list[str], token: str) -> None:
    if token and token not in tokens:
        tokens.append(token)


def _tokenize(text: str) -> list[str]:
    """
    Unicode-aware tokenizer for Chinese, English, and other languages.
    """
    normalized = _normalize_text(text)
    tokens: list[str] = []

    for part in re.findall(r"\w+", normalized, flags=re.UNICODE):
        for run, is_cjk in _script_runs(part):
            if is_cjk:
                for token in _expand_cjk_run(run):
                    _append_unique(tokens, token)
                continue

            _append_unique(tokens, run)
            ascii_alias = _strip_diacritics(run)
            if ascii_alias != run:
                _append_unique(tokens, ascii_alias)

    return tokens


def _contains_query(text: str, query: str) -> bool:
    normalized_text = _normalize_text(text)
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return False
    if normalized_query in normalized_text:
        return True
    return _strip_diacritics(normalized_query) in _strip_diacritics(normalized_text)


def _get_weight_multipliers(entries: list[LTMEntry], memory_dir) -> list[float]:
    """返回每个条目的权重乘数（1.0 ~ 1.4），懒加载 MemoryWeight."""
    try:
        from core.weight import MemoryWeight
        mw = MemoryWeight(memory_dir)
        return [1.0 + (mw.get_weight(e.id) - 1) * 0.1 for e in entries]
    except Exception:
        return [1.0] * len(entries)


def search_entries(
    entries: list[LTMEntry],
    query: str,
    max_results: int = 20,
    use_weight: bool = True,
    memory_dir=None,
) -> list[LTMEntry]:
    """
    BM25 + 关键词混合搜索，支持权重加成。
    
    Args:
        entries: 待搜索的条目列表
        query: 搜索关键词
        max_results: 最多返回条数
        use_weight: 是否应用权重加成
        memory_dir: 内存目录（用于加载权重）
    """
    if not entries:
        return []
    
    if not query or not query.strip():
        if use_weight and memory_dir:
            return _sort_by_weight(entries, memory_dir)[:max_results]
        return entries[:max_results]

    query_tokens = _tokenize(query)
    if not query_tokens:
        if use_weight and memory_dir:
            return _sort_by_weight(entries, memory_dir)[:max_results]
        return entries[:max_results]

    # 关键词评分
    def _relevance_score(entry: LTMEntry, query_token: str) -> int:
        score = 0
        if _contains_query(entry.content, query_token):
            score += 3
        if any(_contains_query(tag, query_token) for tag in entry.tags):
            score += 2
        if _contains_query(entry.category, query_token):
            score += 1
        return score

    keyword_scores = [
        sum(_relevance_score(entry, tok) for tok in query_tokens)
        for entry in entries
    ]

    # BM25 搜索
    if _BM25_AVAILABLE and len(entries) >= 1:
        corpus = [
            _tokenize(f"{e.content} {' '.join(e.tags)} {e.category}")
            for e in entries
        ]
        bm25 = _BM25Okapi(corpus)
        scores = bm25.get_scores(query_tokens)

        for i, entry in enumerate(entries):
            if any(_contains_query(tag, token) for tag in entry.tags for token in query_tokens):
                scores[i] += 0.5

        # 权重加成
        weight_multipliers = _get_weight_multipliers(entries, memory_dir) if use_weight else None

        combined: list[tuple[float, float, float, int, LTMEntry]] = []
        for i, entry in enumerate(entries):
            bm25_score = max(float(scores[i]), 0.0)
            keyword_score = keyword_scores[i]
            relevance = bm25_score + keyword_score
            w_mult = weight_multipliers[i] if weight_multipliers else 1.0
            total_score = relevance * w_mult
            if total_score > 0:
                combined.append((total_score, bm25_score, keyword_score, i, entry))

        combined.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
        return [entry for _, _, _, _, entry in combined[:max_results]]

    # 回退到关键词评分
    weight_multipliers = _get_weight_multipliers(entries, memory_dir) if use_weight else None
    results = []
    for i in range(len(entries)):
        if keyword_scores[i] > 0:
            w_mult = weight_multipliers[i] if weight_multipliers else 1.0
            results.append((keyword_scores[i] * w_mult, entries[i]))
    results.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in results[:max_results]]


def _sort_by_weight(entries: list[LTMEntry], memory_dir) -> list[LTMEntry]:
    """无查询词时，仅按权重降序排列条目。"""
    try:
        from core.weight import MemoryWeight
        mw = MemoryWeight(memory_dir)
        return sorted(entries, key=lambda e: mw.get_weight(e.id), reverse=True)
    except Exception:
        return entries

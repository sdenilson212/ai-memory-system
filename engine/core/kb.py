"""
core/kb.py — Knowledge Base Manager
知识库管理器

职责 (Responsibility):
    管理 knowledge-base.md，提供知识条目的增删改查和文本批量导入。

暴露接口 (Exposes):
    KBManager.add(...)         -> KBEntry
    KBManager.search(...)      -> list[KBEntry]
    KBManager.update(...)      -> KBEntry
    KBManager.delete(...)      -> bool
    KBManager.get_index()      -> list[dict]
    KBManager.import_text(...) -> list[KBEntry]

依赖 (Depends on):
    python-frontmatter, pathlib, re (stdlib)

禁止 (Must NOT):
    - 处理加密
    - 调用 ltm.py 或 stm.py
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import frontmatter

# BM25 optional
try:
    from rank_bm25 import BM25Okapi as _BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25Okapi = None  # type: ignore
    _BM25_AVAILABLE = False


def _tokenize(text: str) -> list[str]:
    """Shared tokenizer: lowercase + split on non-alphanumeric + per-char Chinese."""
    text = text.lower()
    tokens: list[str] = []
    for part in re.split(r"[^\w\u4e00-\u9fff]+", text):
        if not part:
            continue
        if re.search(r"[\u4e00-\u9fff]", part):
            tokens.extend(list(part))
        else:
            tokens.append(part)
    return [t for t in tokens if t]


# ─────────────────────────────────────────────────────────────────────────────
# Data Types
# ─────────────────────────────────────────────────────────────────────────────

VALID_KB_CATEGORIES = {
    "personal", "technical", "project", "domain", "reference", "ai-learned"
}

VALID_CONFIDENCE = {"high", "medium", "low"}


@dataclass
class KBEntry:
    """知识库条目 / A knowledge base entry."""
    id: str
    title: str
    content: str
    category: str
    tags: list[str] = field(default_factory=list)
    source: str = "user-upload"         # user-upload | user-typed | ai-extracted | ai-learned
    confidence: str = "high"            # high | medium | low
    confirmed: bool = True
    created_at: str = ""
    updated_at: str = ""


class KBError(Exception):
    """Base exception for KB operations."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# KBManager
# ─────────────────────────────────────────────────────────────────────────────

class KBManager:
    """
    Manages the knowledge base stored in knowledge-base.md.
    管理以 Markdown 文件存储的知识库。

    Usage / 使用示例:
        kb = KBManager(Path("memory-bank"))

        entry = kb.add(
            title="FastAPI Best Practices",
            content="Use dependency injection for DB sessions...",
            category="technical",
            tags=["fastapi", "python", "backend"],
        )

        results = kb.search("fastapi")
        index   = kb.get_index()
    """

    _KB_FILENAME = "knowledge-base.md"
    # 导入大段文本时，按段落拆分的最小字符数
    _IMPORT_MIN_CHUNK = 100

    def __init__(self, memory_dir: Path) -> None:
        """
        Args:
            memory_dir: 记忆库根目录（包含 knowledge-base.md）。
        """
        self._memory_dir = Path(memory_dir)
        self._kb_path = self._memory_dir / self._KB_FILENAME
        self._memory_dir.mkdir(parents=True, exist_ok=True)

    # ── Public Interface ──────────────────────────────────────────────────────

    def add(
        self,
        title: str,
        content: str,
        category: str = "personal",
        tags: list[str] | None = None,
        source: str = "user-upload",
        confidence: str = "high",
        confirmed: bool = True,
    ) -> KBEntry:
        """
        Add a new entry to the knowledge base.
        向知识库添加新条目。

        Args:
            title:      条目标题（简短描述性名称）。
            content:    条目全文内容。
            category:   分类（personal/technical/project/domain/reference/ai-learned）。
            tags:       自由标签列表。
            source:     来源（user-upload/user-typed/ai-extracted/ai-learned）。
            confidence: 置信度（high/medium/low，主要用于 AI 学习的内容）。
            confirmed:  是否经用户确认（AI 学习内容默认为 False 直到用户确认）。

        Returns:
            新创建的 KBEntry。

        Raises:
            ValueError: 参数不合法时。
            KBError:    文件写入失败时。
        """
        if not title or not title.strip():
            raise ValueError("title must not be empty.")
        if not content or not content.strip():
            raise ValueError("content must not be empty.")
        if category not in VALID_KB_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_KB_CATEGORIES}.")
        if confidence not in VALID_CONFIDENCE:
            raise ValueError(f"confidence must be one of {VALID_CONFIDENCE}.")

        entries = self._load_entries()

        # ── Deduplication guard ────────────────────────────────────────────────
        # Normalize content for comparison (strip + collapse whitespace)
        normalized_new = re.sub(r"\s+", " ", content.strip().lower())
        for existing in entries:
            normalized_existing = re.sub(r"\s+", " ", existing.content.strip().lower())
            if normalized_existing == normalized_new:
                # Duplicate detected — return the existing entry silently
                return existing

        entry = KBEntry(
            id=str(uuid.uuid4()),
            title=title.strip(),
            content=content.strip(),
            category=category,
            tags=tags or [],
            source=source,
            confidence=confidence,
            confirmed=confirmed,
            created_at=_now_iso(),
            updated_at=_now_iso(),
        )

        entries.append(entry)
        self._save_entries(entries)
        return entry

    def search(
        self,
        query: str,
        category: str | None = None,
        top_k: int = 5,
        confirmed_only: bool = True,
    ) -> list[KBEntry]:
        """
        BM25-powered search across all knowledge base entries.
        使用 BM25 算法搜索知识库（自动降级为关键词评分）。

        Args:
            query:          搜索关键词（大小写不敏感，支持中英文混合多词）。
            category:       可选，限制搜索分类。
            top_k:          最多返回条数。
            confirmed_only: 是否只返回经确认的条目。

        Returns:
            匹配的 KBEntry 列表，按 BM25 相关性降序。
        """
        if not query or not query.strip():
            return self.list_all(category=category, limit=top_k)

        all_entries = self._load_entries()
        pool = [
            e for e in all_entries
            if (not confirmed_only or e.confirmed)
            and (not category or e.category == category)
        ]
        if not pool:
            return []

        query_tokens = _tokenize(query)

        if _BM25_AVAILABLE and len(pool) >= 1:
            corpus = [
                _tokenize(f"{e.title} {e.content} {' '.join(e.tags)} {e.category}")
                for e in pool
            ]
            bm25 = _BM25Okapi(corpus)
            scores = bm25.get_scores(query_tokens)

            # Title exact-match bonus
            for i, entry in enumerate(pool):
                if any(t in entry.title.lower() for t in query_tokens):
                    scores[i] += 1.0

            ranked = sorted(
                ((scores[i], pool[i]) for i in range(len(pool)) if scores[i] > 0),
                key=lambda x: x[0],
                reverse=True,
            )
            return [e for _, e in ranked[:top_k]]

        # ── Fallback ──────────────────────────────────────────────────────────
        results: list[tuple[float, KBEntry]] = []
        for entry in pool:
            score = sum(self._relevance_score(entry, tok) for tok in query_tokens)
            if score > 0:
                results.append((score, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:top_k]]

    def update(
        self,
        entry_id: str,
        title: str | None = None,
        content: str | None = None,
        tags: list[str] | None = None,
        confirmed: bool | None = None,
    ) -> KBEntry:
        """
        Update an existing knowledge base entry.
        更新现有知识库条目。

        Args:
            entry_id:  要更新的条目 ID。
            title:     新标题（None 表示不修改）。
            content:   新内容（None 表示不修改）。
            tags:      新标签列表（None 表示不修改）。
            confirmed: 更新确认状态（None 表示不修改）。

        Returns:
            更新后的 KBEntry。

        Raises:
            KBError: 如果 entry_id 不存在。
        """
        entries = self._load_entries()
        idx = next((i for i, e in enumerate(entries) if e.id == entry_id), None)
        if idx is None:
            raise KBError(f"KB entry '{entry_id}' not found.")

        entry = entries[idx]
        if title is not None:
            entry.title = title.strip()
        if content is not None:
            entry.content = content.strip()
        if tags is not None:
            entry.tags = tags
        if confirmed is not None:
            entry.confirmed = confirmed
        entry.updated_at = _now_iso()

        entries[idx] = entry
        self._save_entries(entries)
        return entry

    def delete(self, entry_id: str, confirm: bool = False) -> bool:
        """
        Delete a knowledge base entry. Requires confirm=True.
        删除知识库条目，必须 confirm=True 才执行。

        Args:
            entry_id: 要删除的条目 ID。
            confirm:  安全开关。

        Returns:
            True 如果删除成功，False 如果条目不存在。

        Raises:
            ValueError: 如果 confirm=False。
        """
        if not confirm:
            raise ValueError(
                "Deletion requires confirm=True. Safety guard against accidental deletion."
            )

        entries = self._load_entries()
        original_len = len(entries)
        entries = [e for e in entries if e.id != entry_id]

        if len(entries) == original_len:
            return False

        self._save_entries(entries)
        return True

    def get_index(self) -> list[dict]:
        """
        Return a lightweight index of all entries (no full content).
        返回所有条目的轻量索引（不含全文）。

        Returns:
            List of dicts: id, title, category, tags, source, confirmed, created_at
        """
        entries = self._load_entries()
        return [
            {
                "id":         e.id,
                "title":      e.title,
                "category":   e.category,
                "tags":       e.tags,
                "source":     e.source,
                "confidence": e.confidence,
                "confirmed":  e.confirmed,
                "created_at": e.created_at,
            }
            for e in entries
        ]

    def import_text(
        self,
        text: str,
        category: str = "personal",
        source: str = "user-upload",
        title_prefix: str = "Imported",
    ) -> list[KBEntry]:
        """
        Split a large text into chunks and import each as a KB entry.
        将大段文本拆分为段落并批量导入知识库。

        Splitting strategy:
          1. 按双换行（段落）拆分
          2. 过滤掉太短的片段（< _IMPORT_MIN_CHUNK 字符）
          3. 每段用前 50 个字符作为标题

        Args:
            text:         要导入的文本。
            category:     所有导入条目的分类。
            source:       来源标签。
            title_prefix: 自动生成标题的前缀。

        Returns:
            已创建的 KBEntry 列表。

        Raises:
            ValueError: text 为空时。
        """
        if not text or not text.strip():
            raise ValueError("text must not be empty.")

        # 按段落拆分（2个以上换行符）
        chunks = re.split(r"\n{2,}", text.strip())
        chunks = [c.strip() for c in chunks if len(c.strip()) >= self._IMPORT_MIN_CHUNK]

        if not chunks:
            # 文本不够长，作为单条导入
            chunks = [text.strip()]

        created: list[KBEntry] = []
        for i, chunk in enumerate(chunks, start=1):
            # 用前 60 个字符作为标题，超出部分加省略号
            auto_title = (chunk[:57] + "...") if len(chunk) > 60 else chunk
            auto_title = f"{title_prefix} {i}: {auto_title}"
            entry = self.add(
                title=auto_title,
                content=chunk,
                category=category,
                source=source,
            )
            created.append(entry)

        return created

    def list_all(
        self,
        category: str | None = None,
        limit: int = 100,
    ) -> list[KBEntry]:
        """
        List all knowledge base entries, optionally filtered by category.
        列出所有知识库条目，可按分类过滤。
        """
        entries = self._load_entries()
        if category:
            entries = [e for e in entries if e.category == category]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _load_entries(self) -> list[KBEntry]:
        if not self._kb_path.exists():
            return []
        try:
            post = frontmatter.load(str(self._kb_path))
            raw_entries = post.metadata.get("entries", [])
            if not isinstance(raw_entries, list):
                return []
            return [_dict_to_kb_entry(e) for e in raw_entries if isinstance(e, dict)]
        except Exception:
            return []

    def _save_entries(self, entries: list[KBEntry]) -> None:
        try:
            body = ""
            if self._kb_path.exists():
                try:
                    post = frontmatter.load(str(self._kb_path))
                    body = post.content or ""
                except Exception:
                    pass

            metadata = {
                "entries":      [asdict(e) for e in entries],
                "last_updated": _now_iso(),
                "entry_count":  len(entries),
            }
            post = frontmatter.Post(body, **metadata)
            self._kb_path.write_text(
                frontmatter.dumps(post),
                encoding="utf-8",
            )
        except OSError as exc:
            raise KBError(f"Failed to save knowledge base: {exc}") from exc

    def _relevance_score(self, entry: KBEntry, query_lower: str) -> int:
        """
        Relevance scoring:
          +4  title 完全包含 query
          +3  content 包含 query
          +2  tag 包含 query
          +1  category 包含 query
        """
        score = 0
        if query_lower in entry.title.lower():
            score += 4
        if query_lower in entry.content.lower():
            score += 3
        if any(query_lower in tag.lower() for tag in entry.tags):
            score += 2
        if query_lower in entry.category.lower():
            score += 1
        return score


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dict_to_kb_entry(d: dict) -> KBEntry:
    return KBEntry(
        id=d.get("id", str(uuid.uuid4())),
        title=d.get("title", "Untitled"),
        content=d.get("content", ""),
        category=d.get("category", "personal"),
        tags=d.get("tags", []),
        source=d.get("source", "user-upload"),
        confidence=d.get("confidence", "high"),
        confirmed=d.get("confirmed", True),
        created_at=d.get("created_at", _now_iso()),
        updated_at=d.get("updated_at", _now_iso()),
    )

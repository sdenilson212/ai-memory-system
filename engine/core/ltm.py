"""
core/ltm.py — Long-Term Memory Manager
长期记忆管理器

职责 (Responsibility):
    读写 long-term-memory.md，提供记忆条目的 CRUD 操作和用户档案加载。
    敏感内容通过 Encryptor 加密，仅存引用。

暴露接口 (Exposes):
    LTMManager.save(...)   -> LTMEntry
    LTMManager.get(id)     -> LTMEntry | None
    LTMManager.search(...) -> list[LTMEntry]
    LTMManager.update(...) -> LTMEntry
    LTMManager.delete(...) -> bool
    LTMManager.load_profile() -> dict
    LTMManager.list_all(...) -> list[LTMEntry]

依赖 (Depends on):
    python-frontmatter, pathlib, security/encryptor.py, security/detector.py

禁止 (Must NOT):
    - 直接处理 HTTP 请求
    - 调用 kb.py 或 stm.py
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import frontmatter

from security.detector import SensitiveDetector
from security.encryptor import Encryptor

# BM25 is optional — graceful fallback to keyword scoring if not installed
try:
    from rank_bm25 import BM25Okapi as _BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25Okapi = None  # type: ignore
    _BM25_AVAILABLE = False


def _tokenize(text: str) -> list[str]:
    """
    Simple tokenizer: lowercase + split on non-alphanumeric chars.
    Works for both English words and individual Chinese characters.
    简单分词：小写化后按非字母数字字符拆分，中文按字符拆分。
    """
    text = text.lower()
    # Chinese chars are split individually; latin tokens split on spaces/punct
    tokens: list[str] = []
    for part in re.split(r"[^\w\u4e00-\u9fff]+", text):
        if not part:
            continue
        # If the part contains Chinese chars, split each one out
        if re.search(r"[\u4e00-\u9fff]", part):
            tokens.extend(list(part))
        else:
            tokens.append(part)
    return [t for t in tokens if t]


# ─────────────────────────────────────────────────────────────────────────────
# Data Types
# ─────────────────────────────────────────────────────────────────────────────

VALID_CATEGORIES = {"profile", "preference", "project", "decision", "habit", "credential", "other"}


@dataclass
class LTMEntry:
    """长期记忆条目 / A long-term memory entry."""
    id: str
    content: str
    category: str
    source: str                         # user-explicit | ai-detected | user-upload
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    sensitive: bool = False
    encrypted_ref: Optional[str] = None  # entry_id in encrypted.json


class LTMError(Exception):
    """Base exception for LTM operations."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# LTMManager
# ─────────────────────────────────────────────────────────────────────────────

class LTMManager:
    """
    Manages persistent long-term memory stored in a Markdown file.
    管理以 Markdown 文件存储的长期记忆。

    The file format uses YAML front matter for metadata and Markdown body
    for human-readable content.

    Usage / 使用示例:
        ltm = LTMManager(Path("memory-bank"))

        entry = ltm.save(
            content="I prefer concise code with type hints",
            category="preference",
            source="user-explicit",
            tags=["coding", "style"],
        )

        results = ltm.search("code style")
        profile = ltm.load_profile()
    """

    _LTM_FILENAME = "long-term-memory.md"

    def __init__(
        self,
        memory_dir: Path,
        encryptor: Optional[Encryptor] = None,
        detector: Optional[SensitiveDetector] = None,
    ) -> None:
        """
        Args:
            memory_dir: 记忆库根目录（包含 long-term-memory.md）。
            encryptor:  加密器实例，处理敏感条目。不传则自动初始化。
            detector:   敏感信息检测器。不传则自动初始化。
        Raises:
            OSError: 如果目录无法创建。
        """
        self._memory_dir = Path(memory_dir)
        self._ltm_path = self._memory_dir / self._LTM_FILENAME
        self._memory_dir.mkdir(parents=True, exist_ok=True)

        secure_dir = self._memory_dir / "secure"
        self._encryptor = encryptor or Encryptor(secure_dir)
        self._detector  = detector or SensitiveDetector()

    # ── Public Interface ──────────────────────────────────────────────────────

    def save(
        self,
        content: str,
        category: str = "other",
        source: str = "user-explicit",
        tags: list[str] | None = None,
        sensitive: bool | None = None,
        passphrase: str | None = None,
    ) -> LTMEntry:
        """
        Save a new entry to long-term memory.
        保存新条目到长期记忆。

        Args:
            content:     记忆内容。
            category:    分类（profile/preference/project/decision/habit/credential/other）。
            source:      来源（user-explicit/ai-detected/user-upload）。
            tags:        自由标签列表。
            sensitive:   是否敏感。None 表示由 detector 自动判断。
            passphrase:  加密密码短语（sensitive=True 时必须提供）。

        Returns:
            新创建的 LTMEntry。

        Raises:
            ValueError: 参数不合法时。
            LTMError:   文件读写失败时。
        """
        if not content or not content.strip():
            raise ValueError("content must not be empty.")
        if category not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}.")

        # 自动检测敏感信息
        if sensitive is None:
            sensitive = self._detector.is_sensitive(content)

        encrypted_ref = None
        stored_content = content

        if sensitive:
            if not passphrase:
                # 敏感但没有提供 passphrase：存脱敏版本
                stored_content = self._detector.redact(content)
            else:
                encrypted_ref = self._encryptor.encrypt(
                    key=f"ltm_{uuid.uuid4().hex[:8]}",
                    plaintext=content,
                    passphrase=passphrase,
                    category=category,
                )
                stored_content = self._detector.redact(content)

        entry = LTMEntry(
            id=str(uuid.uuid4()),
            content=stored_content,
            category=category,
            source=source,
            tags=tags or [],
            created_at=_now_iso(),
            updated_at=_now_iso(),
            sensitive=sensitive,
            encrypted_ref=encrypted_ref,
        )

        entries = self._load_entries()
        entries.append(entry)
        self._save_entries(entries)

        return entry

    def get(self, entry_id: str) -> Optional[LTMEntry]:
        """
        Retrieve a single entry by ID.
        按 ID 获取单条记忆。

        Args:
            entry_id: LTMEntry.id

        Returns:
            LTMEntry 或 None（如果不存在）。
        """
        entries = self._load_entries()
        return next((e for e in entries if e.id == entry_id), None)

    def search(
        self,
        query: str,
        category: str | None = None,
        max_results: int = 20,
    ) -> list[LTMEntry]:
        """
        BM25-powered search across all memory entries.
        Uses BM25Okapi when rank-bm25 is installed; falls back to keyword scoring.

        BM25 相关性搜索（已安装 rank-bm25 时自动启用，否则降级为关键词评分）。

        Args:
            query:       搜索关键词（大小写不敏感，支持中英文混合多词）。
            category:    可选，限制搜索分类。
            max_results: 最多返回条数。

        Returns:
            匹配的 LTMEntry 列表，按 BM25 相关性降序。
        """
        if not query or not query.strip():
            return self.list_all(category=category)

        all_entries = self._load_entries()
        pool = [e for e in all_entries if not category or e.category == category]
        if not pool:
            return []

        query_tokens = _tokenize(query)

        if _BM25_AVAILABLE and len(pool) >= 1:
            # Build corpus: combine content + title-like prefix + tags per entry
            corpus = [
                _tokenize(f"{e.content} {' '.join(e.tags)} {e.category}")
                for e in pool
            ]
            bm25 = _BM25Okapi(corpus)
            scores = bm25.get_scores(query_tokens)

            # Add field-boost on top of BM25 (tag exact match gets +0.5)
            for i, entry in enumerate(pool):
                tag_str = " ".join(entry.tags).lower()
                if any(t in tag_str for t in query_tokens):
                    scores[i] += 0.5

            ranked = sorted(
                ((scores[i], pool[i]) for i in range(len(pool)) if scores[i] > 0),
                key=lambda x: x[0],
                reverse=True,
            )
            return [e for _, e in ranked[:max_results]]

        # ── Fallback: multi-token keyword scoring ──────────────────────────────
        results: list[tuple[float, LTMEntry]] = []
        for entry in pool:
            score = sum(self._relevance_score(entry, tok) for tok in query_tokens)
            if score > 0:
                results.append((score, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:max_results]]

    def update(
        self,
        entry_id: str,
        content: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
    ) -> LTMEntry:
        """
        Update an existing entry's content or tags.
        更新现有条目的内容或标签。

        Args:
            entry_id: 要更新的条目 ID。
            content:  新内容（None 表示不修改）。
            tags:     新标签列表（None 表示不修改）。
            category: 新分类（None 表示不修改）。

        Returns:
            更新后的 LTMEntry。

        Raises:
            LTMError: 如果 entry_id 不存在。
        """
        entries = self._load_entries()
        idx = next((i for i, e in enumerate(entries) if e.id == entry_id), None)
        if idx is None:
            raise LTMError(f"Entry '{entry_id}' not found.")

        entry = entries[idx]
        if content is not None:
            entry.content = content
        if tags is not None:
            entry.tags = tags
        if category is not None:
            if category not in VALID_CATEGORIES:
                raise ValueError(f"category must be one of {VALID_CATEGORIES}.")
            entry.category = category
        entry.updated_at = _now_iso()

        entries[idx] = entry
        self._save_entries(entries)
        return entry

    def delete(self, entry_id: str, confirm: bool = False) -> bool:
        """
        Delete an entry. Requires confirm=True to actually execute.
        删除条目，必须 confirm=True 才会执行。

        Args:
            entry_id: 要删除的条目 ID。
            confirm:  安全开关，必须显式传 True。

        Returns:
            True 如果删除成功，False 如果条目不存在。

        Raises:
            ValueError: 如果 confirm=False（拒绝删除）。
        """
        if not confirm:
            raise ValueError(
                "Deletion requires confirm=True. "
                "This is a safety guard to prevent accidental deletion."
            )

        entries = self._load_entries()
        original_len = len(entries)
        entries = [e for e in entries if e.id != entry_id]

        if len(entries) == original_len:
            return False

        self._save_entries(entries)
        return True

    def load_profile(self) -> dict:
        """
        Return a summary of the user profile from memory.
        从记忆中返回用户档案摘要。

        Returns:
            dict 包含：name, preferences, active_projects, recent_decisions, habits
        """
        entries = self._load_entries()

        profile_entries     = [e for e in entries if e.category == "profile"]
        preference_entries  = [e for e in entries if e.category == "preference"]
        project_entries     = [e for e in entries if e.category == "project"]
        decision_entries    = [e for e in entries if e.category == "decision"]
        habit_entries       = [e for e in entries if e.category == "habit"]

        return {
            "profile":          [_entry_to_summary(e) for e in profile_entries],
            "preferences":      [_entry_to_summary(e) for e in preference_entries],
            "active_projects":  [_entry_to_summary(e) for e in project_entries],
            "recent_decisions": [_entry_to_summary(e) for e in decision_entries[-5:]],
            "habits":           [_entry_to_summary(e) for e in habit_entries],
            "total_entries":    len(entries),
        }

    def list_all(
        self,
        category: str | None = None,
        limit: int = 100,
    ) -> list[LTMEntry]:
        """
        List all entries, optionally filtered by category.
        列出所有条目，可按分类过滤。

        Args:
            category: 可选，按分类过滤。
            limit:    最多返回条数。

        Returns:
            LTMEntry 列表，按创建时间降序。
        """
        entries = self._load_entries()
        if category:
            entries = [e for e in entries if e.category == category]
        # 最新优先
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _load_entries(self) -> list[LTMEntry]:
        """Load all entries from long-term-memory.md."""
        if not self._ltm_path.exists():
            return []
        try:
            post = frontmatter.load(str(self._ltm_path))
            raw_entries = post.metadata.get("entries", [])
            if not isinstance(raw_entries, list):
                return []
            return [_dict_to_entry(e) for e in raw_entries if isinstance(e, dict)]
        except Exception:
            return []

    def _save_entries(self, entries: list[LTMEntry]) -> None:
        """Persist all entries to long-term-memory.md."""
        try:
            # 保留现有的 Markdown 正文（如有）
            body = ""
            if self._ltm_path.exists():
                try:
                    post = frontmatter.load(str(self._ltm_path))
                    body = post.content or ""
                except Exception:
                    pass

            metadata = {
                "entries": [asdict(e) for e in entries],
                "last_updated": _now_iso(),
                "entry_count": len(entries),
            }

            post = frontmatter.Post(body, **metadata)
            self._ltm_path.write_text(
                frontmatter.dumps(post),
                encoding="utf-8",
            )
        except OSError as exc:
            raise LTMError(f"Failed to save long-term memory: {exc}") from exc

    def _relevance_score(self, entry: LTMEntry, query_lower: str) -> int:
        """
        Simple relevance scoring for keyword search.
        关键词搜索的简单相关性评分。

        Scoring:
          +3  content 完全包含 query
          +2  任意 tag 包含 query
          +1  category 包含 query
        """
        score = 0
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


def _dict_to_entry(d: dict) -> LTMEntry:
    return LTMEntry(
        id=d.get("id", str(uuid.uuid4())),
        content=d.get("content", ""),
        category=d.get("category", "other"),
        source=d.get("source", "user-explicit"),
        tags=d.get("tags", []),
        created_at=d.get("created_at", _now_iso()),
        updated_at=d.get("updated_at", _now_iso()),
        sensitive=d.get("sensitive", False),
        encrypted_ref=d.get("encrypted_ref"),
    )


def _entry_to_summary(entry: LTMEntry) -> dict:
    return {
        "id":         entry.id,
        "content":    entry.content,
        "tags":       entry.tags,
        "created_at": entry.created_at,
    }

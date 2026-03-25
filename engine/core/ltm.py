"""
core/ltm.py — Long-Term Memory Manager
长期记忆管理器

v1.1 改进（2026-03-25）：
  1. 并发安全：添加 SafeFileWriter 文件锁（WAL 模式）
  2. SQLite 索引：新增 _index.db，O(log n) 搜索加速
  3. 语义搜索路由：集成 VectorStore，关键词/向量双模式自动切换
  4. Passphrase 管理：支持环境变量 / keyring 双通道获取

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
    python-frontmatter, pathlib, security/encryptor.py, security/detector.py,
    filelock, sqlite3 (内置)

禁止 (Must NOT):
    - 直接处理 HTTP 请求
    - 调用 kb.py 或 stm.py
"""

from __future__ import annotations

import json
import re
import uuid
import sqlite3
import os
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import frontmatter
from filelock import FileLock

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
# SafeFileWriter — 并发安全写入（WAL 模式）
# ─────────────────────────────────────────────────────────────────────────────

class SafeFileWriter:
    """
    线程/进程安全的文件写入器。
    使用 filelock 文件锁 + 操作日志（WAL），防止并发写冲突和数据丢失。
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.wal_path = self.path.with_suffix(self.path.suffix + ".wal")

    def write(self, content: str) -> None:
        """原子写入：WAL → 主文件 → 清理 WAL"""
        lock = FileLock(str(self.lock_path), timeout=10)
        with lock:
            # 1. 追加 WAL 日志（故障恢复用）
            wal_mode = os.environ.get("AI_MEMORY_WAL", "1") == "1"
            if wal_mode:
                wal_entry = json.dumps({
                    "ts": _now_iso(),
                    "content": content
                }, ensure_ascii=False)
                with open(self.wal_path, "a", encoding="utf-8") as wf:
                    wf.write(wal_entry + "\n")

            # 2. 写入主文件
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(content, encoding="utf-8")

            # 3. 清理 WAL（写入成功）
            if wal_mode and self.wal_path.exists():
                try:
                    self.wal_path.unlink()
                except OSError:
                    pass

    def recover_from_wal(self) -> None:
        """从 WAL 恢复最后一次写入"""
        if not self.wal_path.exists():
            return
        try:
            lines = self.wal_path.read_text(encoding="utf-8").strip().splitlines()
            if lines:
                last = json.loads(lines[-1])
                self.path.write_text(last["content"], encoding="utf-8")
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# SQLite 索引层 — O(log n) 搜索
# ─────────────────────────────────────────────────────────────────────────────

class LTMIndex:
    """
    SQLite 索引：对 LTM 条目建立 id / category / tags / created_at 索引。
    不存 content（防止隐私泄露），只存搜索元数据。
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ltm_index (
                    id          TEXT PRIMARY KEY,
                    category    TEXT NOT NULL,
                    tags        TEXT NOT NULL DEFAULT '',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    is_sensitive INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON ltm_index(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON ltm_index(created_at DESC)")
            conn.commit()

    def upsert(self, entry: LTMEntry) -> None:
        import hashlib
        content_hash = hashlib.sha256(entry.content.encode()).hexdigest()[:16]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ltm_index
                (id, category, tags, created_at, updated_at, content_hash, is_sensitive)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.category,
                ",".join(entry.tags),
                entry.created_at,
                entry.updated_at,
                content_hash,
                int(entry.sensitive)
            ))
            conn.commit()

    def delete(self, entry_id: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM ltm_index WHERE id = ?", (entry_id,))
            conn.commit()

    def search_by_category(self, category: str, limit: int = 100) -> list[str]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id FROM ltm_index WHERE category = ? ORDER BY created_at DESC LIMIT ?",
                (category, limit)
            ).fetchall()
        return [r[0] for r in rows]

    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM ltm_index").fetchone()[0]
            by_cat = dict(conn.execute(
                "SELECT category, COUNT(*) FROM ltm_index GROUP BY category"
            ).fetchall())
        return {"total": total, "by_category": by_cat}

    def search_by_tags(self, tags: list[str], limit: int = 50) -> list[str]:
        if not tags:
            return []
        placeholders = ",".join(["?"] * len(tags))
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT id FROM ltm_index WHERE tags REGEXP ? ORDER BY created_at DESC LIMIT ?",
                ("|".join(tags), limit)
            ).fetchall()
        return [r[0] for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Passphrase 管理器
# ─────────────────────────────────────────────────────────────────────────────

def get_passphrase() -> Optional[str]:
    """
    从环境变量或系统 keyring 获取 passphrase。
    Level 1: 环境变量 AI_MEMORY_PASSPHRASE
    Level 2: 系统 keyring（keyring 库）
    """
    # Level 1: 环境变量
    p = os.environ.get("AI_MEMORY_PASSPHRASE")
    if p:
        return p

    # Level 2: keyring（keyring 库）
    try:
        import keyring
        p = keyring.get_password("ai-memory-system", "passphrase")
        if p:
            return p
    except Exception:
        pass

    return None


# ─────────────────────────────────────────────────────────────────────────────
# LTMManager
# ─────────────────────────────────────────────────────────────────────────────

class LTMManager:
    """
    Manages persistent long-term memory stored in a Markdown file.
    管理以 Markdown 文件存储的长期记忆。

    v1.1 改进：
      - SafeFileWriter：并发安全的文件写入（WAL 模式）
      - SQLite 索引：搜索从 O(n) → O(log n)
      - 语义搜索路由：关键词模式 + 向量模式（通过 vector_store 参数）
      - Passphrase 管理：环境变量 / keyring 双通道

    Usage / 使用示例:
        ltm = LTMManager(Path("memory-bank"))
        # 注入 VectorStore 实现语义搜索
        ltm.vector_store = vector_store_instance

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
            memory_dir: 记忆库根目录（包含 long-term-memory.md 和 index.db）。
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

        # v1.1: 安全文件写入器
        self._writer = SafeFileWriter(self._ltm_path)

        # v1.1: SQLite 索引层
        self._index = LTMIndex(self._memory_dir / "index.db")

        # v1.1: 向量存储（可选，由外部注入）
        self.vector_store = None
        self._search_mode = "auto"  # "keyword" | "vector" | "hybrid" | "auto"

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

        v1.1: 自动同步 SQLite 索引
        """
        if not content or not content.strip():
            raise ValueError("content must not be empty.")
        if category not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}.")

        # 敏感检测
        if sensitive is None:
            sensitive = self._detector.is_sensitive(content)

        encrypted_ref = None
        stored_content = content

        if sensitive:
            # 优先用传入的 passphrase，否则从环境变量/keyring 获取
            _pass = passphrase or get_passphrase()
            if _pass:
                encrypted_ref = self._encryptor.encrypt(
                    key=f"ltm_{uuid.uuid4().hex[:8]}",
                    plaintext=content,
                    passphrase=_pass,
                    category=category,
                )
                stored_content = self._detector.redact(content)
            else:
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

        # v1.1: 同步索引
        self._index.upsert(entry)

        return entry

    def get(self, entry_id: str) -> LTMEntry | None:
        """Retrieve a single entry by ID."""
        entries = self._load_entries()
        return next((e for e in entries if e.id == entry_id), None)

    def search(
        self,
        query: str,
        category: str | None = None,
        max_results: int = 20,
        mode: str = "auto",
    ) -> list[LTMEntry]:
        """
        Search long-term memory using configurable mode.

        Modes:
          - "auto": 短查询（< 20字）用向量，长查询用关键词/混合
          - "keyword": BM25 + 关键词评分（快速、精确）
          - "vector": 纯向量语义搜索（需要 vector_store 已注入）
          - "hybrid": 关键词 + 向量加权融合（最佳效果）

        v1.1: 语义路由 + SQLite 预过滤
        """
        if not query or not query.strip():
            return self.list_all(category=category)

        # v1.1: 先用 SQLite 索引过滤分类，减少搜索范围
        pool_ids = None
        if category:
            pool_ids = set(self._index.search_by_category(category))

        # 路由搜索模式
        effective_mode = mode
        if mode == "auto":
            effective_mode = "vector" if len(query) < 20 and self.vector_store else "keyword"

        if effective_mode == "vector" and self.vector_store:
            # 向量搜索
            vector_results = self.vector_store.search(query, top_k=max_results)
            entry_ids = [r["entry_id"] for r in vector_results]
            # 合并分类过滤
            if pool_ids is not None:
                entry_ids = [i for i in entry_ids if i in pool_ids]
            entries = [self.get(eid) for eid in entry_ids if self.get(eid)]
            return entries[:max_results]

        elif effective_mode == "hybrid" and self.vector_store:
            # 混合搜索
            hybrid_results = self.vector_store.hybrid_search(
                query, keyword_results=[], top_k=max_results
            )
            entry_ids = [r.get("entry_id") or r.get("id") for r in hybrid_results]
            if pool_ids is not None:
                entry_ids = [i for i in entry_ids if i in pool_ids]
            entries = [self.get(eid) for eid in entry_ids if self.get(eid)]
            return entries[:max_results]

        # 关键词 / BM25 搜索（原始逻辑）
        all_entries = self._load_entries()
        pool = [e for e in all_entries if not category or e.category == category]
        if not pool:
            return []

        query_tokens = _tokenize(query)

        if _BM25_AVAILABLE and len(pool) >= 1:
            corpus = [
                _tokenize(f"{e.content} {' '.join(e.tags)} {e.category}")
                for e in pool
            ]
            bm25 = _BM25Okapi(corpus)
            scores = bm25.get_scores(query_tokens)

            # 标签 Boost（命中学到 +0.5）
            for i, entry in enumerate(pool):
                tag_str = " ".join(entry.tags).lower()
                if any(t in tag_str for t in query_tokens):
                    scores[i] += 0.5

            ranked = sorted(
                ((scores[i], pool[i]) for i in range(len(pool)) if scores[i] > 0),
                key=lambda x: x[0], reverse=True,
            )
            return [e for _, e in ranked[:max_results]]

        # Fallback: 多token关键词评分
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
        """Update an existing entry's content or tags."""
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
        self._index.upsert(entry)
        return entry

    def delete(self, entry_id: str, confirm: bool = False) -> bool:
        """Delete an entry. Requires confirm=True to execute."""
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
        self._index.delete(entry_id)
        return True

    def load_profile(self) -> dict:
        """Return a summary of the user profile from memory."""
        entries = self._load_entries()

        profile_entries     = [e for e in entries if e.category == "profile"]
        pref_entries        = [e for e in entries if e.category == "preference"]
        project_entries     = [e for e in entries if e.category == "project"]
        decision_entries    = [e for e in entries if e.category == "decision"]
        habit_entries       = [e for e in entries if e.category == "habit"]

        return {
            "profile":              [_entry_to_summary(e) for e in profile_entries],
            "preferences":          [_entry_to_summary(e) for e in pref_entries],
            "active_projects":      [_entry_to_summary(e) for e in project_entries],
            "recent_decisions":     [_entry_to_summary(e) for e in decision_entries[-5:]],
            "habits":               [_entry_to_summary(e) for e in habit_entries],
            "total_entries":       len(entries),
        }

    def list_all(
        self,
        category: str | None = None,
        limit: int = 100,
    ) -> list[LTMEntry]:
        """List all entries, optionally filtered by category."""
        entries = self._load_entries()
        if category:
            entries = [e for e in entries if e.category == category]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    def get_stats(self) -> dict:
        """返回系统统计信息"""
        file_count = len(self._load_entries())
        index_stats = self._index.get_stats()
        return {
            "file_entries": file_count,
            "index_total": index_stats["total"],
            "by_category": index_stats["by_category"],
        }

    # ── Private Helpers ────────────────────────────────────────────────────────

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
        """Persist all entries to long-term-memory.md using SafeFileWriter."""
        try:
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
            content = frontmatter.dumps(post)

            # v1.1: 使用 SafeFileWriter 写入
            self._writer.write(content)

        except OSError as exc:
            raise LTMError(f"Failed to save long-term memory: {exc}") from exc

    def _relevance_score(self, entry: LTMEntry, tok: str) -> int:
        """
        Simple relevance scoring for keyword search.
        Scoring:
          +3 content 命中 query
          +2 tag      命中 query
          +1 category 命中 query
        """
        score = 0
        if tok in entry.content.lower():
            score += 3
        if any(tok in tag.lower() for tag in entry.tags):
            score += 2
        if tok in entry.category.lower():
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
        "id":          entry.id,
        "content":     entry.content,
        "tags":        entry.tags,
        "created_at":  entry.created_at,
    }

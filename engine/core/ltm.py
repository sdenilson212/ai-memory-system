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
import unicodedata
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


import frontmatter
import logging

from security.detector import SensitiveDetector
from security.encryptor import Encryptor

logger = logging.getLogger(__name__)


def _load_frontmatter_file(path: Path):
    """Load front matter via UTF-8 text to avoid frontmatter.load() deprecation noise."""
    return frontmatter.loads(path.read_text(encoding="utf-8"))


# ── 并发安全：文件锁 ──────────────────────────────────────────────────────────
# 使用 filelock 保证多进程/多客户端同时读写时不丢数据。
# 如果 filelock 未安装，降级为无锁（单进程场景安全）。
try:
    from filelock import FileLock as _FileLock
    _FILELOCK_AVAILABLE = True
except ImportError:
    _FileLock = None  # type: ignore
    _FILELOCK_AVAILABLE = False

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
    current_is_cjk: Optional[bool] = None

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
    - NFKC + casefold normalization
    - Preserve word tokens for spaced languages
    - Split CJK runs into searchable chars/bigrams/full-run tokens
    - Add accent-folded aliases for Latin-based languages
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
    similar_to: Optional[str] = None    # 引用相似条目的 ID，用于去重跟踪


class LTMError(Exception):
    """Base exception for LTM operations."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# LTMManager
# ─────────────────────────────────────────────────────────────────────────────

class LTMManager:
    """
    Manages persistent long-term memory stored in sharded Markdown files.
    管理以 Markdown 文件分片存储的长期记忆。

    存储策略（分片）：
        每个 category 对应一个独立文件，避免单文件无限增长：
            long-term-memory-profile.md
            long-term-memory-preference.md
            long-term-memory-project.md
            long-term-memory-decision.md
            long-term-memory-habit.md
            long-term-memory-credential.md
            long-term-memory-other.md
        兼容旧版单文件 long-term-memory.md（自动迁移）。

    并发安全：
        使用 filelock（如已安装）对每个分片文件加写锁，防止多进程同时写入导致数据丢失。
        未安装 filelock 时降级为无锁（单进程场景安全）。

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

    _LTM_FILENAME = "long-term-memory.md"          # 旧版兼容文件
    _SHARD_PREFIX = "long-term-memory-"             # 分片文件前缀
    _SHARD_SUFFIX = ".md"

    def __init__(
        self,
        memory_dir: Path,
        encryptor: Optional[Encryptor] = None,
        detector: Optional[SensitiveDetector] = None,
    ) -> None:
        """
        Args:
            memory_dir: 记忆库根目录。
            encryptor:  加密器实例，处理敏感条目。不传则自动初始化。
            detector:   敏感信息检测器。不传则自动初始化。
        Raises:
            OSError: 如果目录无法创建。
        """
        self._memory_dir = Path(memory_dir)
        self._ltm_path = self._memory_dir / self._LTM_FILENAME  # 兼容旧文件
        self._memory_dir.mkdir(parents=True, exist_ok=True)

        secure_dir = self._memory_dir / "secure"
        self._encryptor = encryptor or Encryptor(secure_dir)
        self._detector  = detector or SensitiveDetector()

        # 初始化语义向量存储（v1.6.0）
        self._vector_store: Optional[Any] = None
        self._init_vector_store()

        # 首次初始化时，将旧版单文件数据迁移到分片
        self._migrate_legacy_file()
    
    def _init_vector_store(self) -> None:
        """初始化语义向量存储（可选，失败不阻塞）"""
        import logging
        _logger = logging.getLogger(__name__)
        try:
            from core.vector_store import SemanticVectorStore
            vector_dir = self._memory_dir / "vectors"
            self._vector_store = SemanticVectorStore(vector_dir)
            _logger.info("Vector store initialized for semantic search")
        except Exception as e:
            _logger.warning(f"Vector store init failed: {e}, semantic search disabled")
            self._vector_store = None

    # ── 分片路径工具 ──────────────────────────────────────────────────────────

    def _shard_path(self, category: str) -> Path:
        """返回指定 category 对应的分片文件路径。"""
        safe_cat = re.sub(r"[^\w-]", "_", category)  # 防止路径注入
        return self._memory_dir / f"{self._SHARD_PREFIX}{safe_cat}{self._SHARD_SUFFIX}"

    def _lock_for(self, path: Path):
        """返回指定文件的锁（contextmanager）。无 filelock 时返回空上下文。"""
        if _FILELOCK_AVAILABLE:
            # 增加超时时间，避免高并发场景锁竞争失败
            # 基准测试中 32 个线程竞争同一把锁，30 秒应该足够
            return _FileLock(str(path) + ".lock", timeout=30)
        return _NullLock()

    def _migrate_legacy_file(self) -> None:
        """
        将旧版 long-term-memory.md 中的条目迁移到对应分片文件。
        迁移完成后重命名旧文件为 long-term-memory.migrated.md，避免重复迁移。
        """
        if not self._ltm_path.exists():
            return
        migrated_path = self._memory_dir / "long-term-memory.migrated.md"
        if migrated_path.exists():
            return  # 已迁移过

        try:
            post = _load_frontmatter_file(self._ltm_path)

            raw_entries = post.metadata.get("entries", [])
            if not isinstance(raw_entries, list) or not raw_entries:
                self._ltm_path.rename(migrated_path)
                return

            # 按 category 分组写入分片
            from collections import defaultdict
            by_cat: dict[str, list] = defaultdict(list)
            for e in raw_entries:
                if isinstance(e, dict):
                    by_cat[e.get("category", "other")].append(e)

            for cat, entries in by_cat.items():
                existing = self._load_shard(cat)
                existing_ids = {e.id for e in existing}
                new_entries = [
                    _dict_to_entry(e) for e in entries
                    if e.get("id") not in existing_ids
                ]
                if new_entries:
                    self._save_shard(cat, existing + new_entries)

            self._ltm_path.rename(migrated_path)
        except Exception as exc:
            # P0 修复：异常不能被静默吞掉，必须记录日志
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"LTM 旧文件迁移失败：{exc}", exc_info=True)
            # 继续正常启动（不影响现有记忆读写），但保留原始异常信息

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

        # passphrase 优先级：显式传入 > 环境变量 MEMORY_PASSPHRASE > None（降级脱敏存储）
        resolved_passphrase = Encryptor.get_passphrase(explicit=passphrase)

        # 分片优化：在同一把锁里完成读 + 去重检查 + 创建条目 + 追加写入，确保原子性
        path = self._shard_path(category)
        try:
            with self._lock_for(path):
                # 在锁内加载现有条目
                existing_entries: list[LTMEntry] = []
                raw_entries: list[dict] = []
                if path.exists():
                    try:
                        post = _load_frontmatter_file(path)
                        loaded = post.metadata.get("entries", [])
                        if isinstance(loaded, list):
                            raw_entries = [item for item in loaded if isinstance(item, dict)]
                            existing_entries = [_dict_to_entry(item) for item in raw_entries]
                    except Exception:
                        raw_entries = []
                
                # P0 修复：去重检查（必须在锁内执行，避免并发竞态）
                # v2.0 修复：不再返回现有条目，改为创建新条目并标记相似性
                similar_to_id = None
                try:
                    from core.deduplicator import Deduplicator
                    dedup = Deduplicator(similarity_threshold=0.85, method="cosine")
                    
                    existing_contents = [e.content for e in existing_entries]
                    
                    if dedup.is_duplicate(content, existing_contents):
                        # 找到高度相似条目，记录相似条目 ID，继续创建新条目
                        duplicates = dedup.find_duplicates(content, existing_contents)
                        if duplicates:
                            best_match = duplicates[0]
                            match_index = best_match["index"]
                            if 0 <= match_index < len(existing_entries):
                                similar_to_id = existing_entries[match_index].id
                                # 记录日志但不中断保存流程
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.debug(
                                    f"Found similar entry (similarity={best_match.get('similarity', 0.0):.2f}) "
                                    f"for content: {content[:50]}..."
                                )
                except ImportError:
                    # Deduplicator 未安装（非致命错误），继续正常保存流程
                    pass
                except Exception as dedup_exc:
                    # 去重模块发生未知错误，记录日志并继续正常保存（不阻断核心功能）
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"Deduplicator error (non-fatal): {dedup_exc}")
                    pass

                # 处理敏感信息和加密
                encrypted_ref = None
                stored_content = content

                if sensitive:
                    if not resolved_passphrase:
                        # 敏感但没有提供 passphrase：存脱敏版本
                        stored_content = self._detector.redact(content)
                    else:
                        encrypted_ref = self._encryptor.encrypt(
                            key=f"ltm_{uuid.uuid4().hex[:8]}",
                            plaintext=content,
                            passphrase=resolved_passphrase,
                            category=category,
                        )
                        stored_content = self._detector.redact(content)

                # 创建新条目
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
                    similar_to=similar_to_id,  # 记录相似条目 ID（如果存在）
                )

                raw_entries.append(asdict(entry))
                metadata = {
                    "category": category,
                    "entries": raw_entries,
                    "last_updated": _now_iso(),
                    "entry_count": len(raw_entries),
                }
                post = frontmatter.Post("", **metadata)
                path.write_text(frontmatter.dumps(post), encoding="utf-8")
                
                # ── v1.6.0: 同步到向量存储（锁外异步）
                self._sync_to_vector_store(entry)
                
                return entry
                
        except OSError as exc:
            raise LTMError(f"Failed to save shard '{category}': {exc}") from exc
        except Exception as exc:
            # 捕获可能的 Timeout 或其他异常
            if _FILELOCK_AVAILABLE and "Timeout" in str(type(exc).__name__):
                raise LTMError(f"Failed to acquire lock for shard '{category}' (timeout): {exc}") from exc
            raise LTMError(f"Unexpected error saving to shard '{category}': {exc}") from exc


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
        use_weight: bool = True,
        use_semantic: bool = False,
        semantic_weight: float = 0.6,
    ) -> list[LTMEntry]:
        """
        BM25-powered search across all memory entries.
        Uses BM25Okapi when rank-bm25 is installed; falls back to keyword scoring.
        Optionally applies MemoryWeight boost so high-importance entries rank higher.
        Supports semantic search (v1.6.0) via sentence-transformers + ChromaDB.

        BM25 相关性搜索（已安装 rank-bm25 时自动启用，否则降级为关键词评分）。
        支持权重加成：高重要性条目在相关性相近时优先排序。
        支持语义搜索（v1.6.0）：模糊查询、同义词理解。

        Args:
            query:       搜索关键词（大小写不敏感，支持中英文混合多词）。
            category:    可选，限制搜索分类。
            max_results: 最多返回条数。
            use_weight:  是否应用 MemoryWeight 权重加成（默认 True）。
            use_semantic: 是否启用语义搜索（默认 False）。
            semantic_weight: 语义分数权重，0-1（默认 0.6）。

        Returns:
            匹配的 LTMEntry 列表，按 BM25 相关性降序（可叠加权重加成）。
        """
        # 分片优化：有 category 时只扫描对应分片，没有时全量
        all_entries = self._load_shard(category) if category else self._load_entries()
        pool = all_entries
        if not pool:
            return []
        if not query or not query.strip():
            # 无查询词时：直接按权重返回（如果启用）
            if use_weight:
                return self._sort_by_weight(pool)[:max_results]
            return pool[:max_results]
        
        # ── v1.6.0: 语义搜索支持 ─────────────────────────────────────────────
        if use_semantic and self._vector_store and self._vector_store.semantic_enabled:
            return self._hybrid_search(
                query=query,
                pool=pool,
                max_results=max_results,
                use_weight=use_weight,
                semantic_weight=semantic_weight,
            )

        query_tokens = _tokenize(query)
        if not query_tokens:
            if use_weight:
                return self._sort_by_weight(pool)[:max_results]
            return pool[:max_results]

        keyword_scores = [
            sum(self._relevance_score(entry, tok) for tok in query_tokens)
            for entry in pool
        ]

        if _BM25_AVAILABLE and len(pool) >= 1:
            # Build corpus: combine content + title-like prefix + tags per entry
            corpus = [
                _tokenize(f"{e.content} {' '.join(e.tags)} {e.category}")
                for e in pool
            ]
            bm25 = _BM25Okapi(corpus)
            scores = bm25.get_scores(query_tokens)

            # Add field-boost on top of BM25 (normalized tag match gets +0.5)
            for i, entry in enumerate(pool):
                if any(_contains_query(tag, token) for tag in entry.tags for token in query_tokens):
                    scores[i] += 0.5

            # ── 权重加成（v1.5.0）────────────────────────────────────────────
            weight_multipliers = self._get_weight_multipliers(pool) if use_weight else None

            combined: list[tuple[float, float, float, int, LTMEntry]] = []
            for i, entry in enumerate(pool):
                bm25_score = max(float(scores[i]), 0.0)
                keyword_score = keyword_scores[i]
                relevance = bm25_score + keyword_score
                # 权重乘数：1.0（无加成）到 1.4（CORE权重，+40%提升）
                w_mult = weight_multipliers[i] if weight_multipliers else 1.0
                total_score = relevance * w_mult
                if total_score > 0:
                    combined.append((total_score, bm25_score, keyword_score, i, entry))

            combined.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
            return [entry for _, _, _, _, entry in combined[:max_results]]

        # ── Fallback: multi-token keyword scoring ──────────────────────────────

        weight_multipliers = self._get_weight_multipliers(pool) if use_weight else None
        results = []
        for i in range(len(pool)):
            if keyword_scores[i] > 0:
                w_mult = weight_multipliers[i] if weight_multipliers else 1.0
                results.append((keyword_scores[i] * w_mult, pool[i]))
        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:max_results]]

    def recall(self, query: str, max_results: int = 20) -> list[LTMEntry]:
        """
        Recall memories matching the query.
        这是 search() 的别名，保持 API 兼容性。

        Args:
            query:       搜索关键词。
            max_results: 最多返回条数。

        Returns:
            匹配的 LTMEntry 列表。
        """
        return self.search(query=query, max_results=max_results)


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
        old_category = entry.category
        if content is not None:
            entry.content = content
        if tags is not None:
            entry.tags = tags
        if category is not None:
            if category not in VALID_CATEGORIES:
                raise ValueError(f"category must be one of {VALID_CATEGORIES}.")
            entry.category = category
        entry.updated_at = _now_iso()

        if old_category != entry.category:
            # category 变了：从旧分片删除，写入新分片
            old_shard = self._load_shard(old_category)
            self._save_shard(old_category, [e for e in old_shard if e.id != entry_id])
            new_shard = self._load_shard(entry.category)
            new_shard.append(entry)
            self._save_shard(entry.category, new_shard)
        else:
            entries[idx] = entry
            self._save_shard(old_category, [e if e.id != entry_id else entry for e in self._load_shard(old_category)])

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

        # 先在全量中找到条目，确定它属于哪个 category 分片
        target: Optional[LTMEntry] = None
        for cat in VALID_CATEGORIES:
            shard = self._load_shard(cat)
            for e in shard:
                if e.id == entry_id:
                    target = e
                    break
            if target:
                break

        if target is None:
            return False

        shard = self._load_shard(target.category)
        new_shard = [e for e in shard if e.id != entry_id]
        if len(new_shard) == len(shard):
            return False

        self._save_shard(target.category, new_shard)
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

    def _load_entries(self, category: Optional[str] = None) -> list[LTMEntry]:
        """
        Load entries from shard file(s).
        从分片文件加载条目。

        Args:
            category: 如果指定，只加载该分类的分片（快速）；
                      如果为 None，加载所有分片（全量扫描）。
        """
        if category:
            return self._load_shard(category)

        # 全量：遍历所有已知 category 的分片
        all_entries: list[LTMEntry] = []
        for cat in VALID_CATEGORIES:
            all_entries.extend(self._load_shard(cat))
        return all_entries

    def _load_shard(self, category: str) -> list[LTMEntry]:
        """从指定 category 的分片文件加载条目（加读锁）。"""
        path = self._shard_path(category)
        if not path.exists():
            return []
        try:
            with self._lock_for(path):
                post = _load_frontmatter_file(path)
            raw_entries = post.metadata.get("entries", [])
            if not isinstance(raw_entries, list):
                return []
            return [_dict_to_entry(e) for e in raw_entries if isinstance(e, dict)]
        except Exception:
            return []

    def _save_entries(self, entries: list[LTMEntry]) -> None:
        """
        Persist entries to shard file(s).
        按 category 分组，写入各自的分片文件。
        """
        from collections import defaultdict
        by_cat: dict[str, list[LTMEntry]] = defaultdict(list)
        for e in entries:
            by_cat[e.category].append(e)

        # 清空不再包含任何条目的分片（避免孤儿文件残留）
        for cat in VALID_CATEGORIES:
            if cat not in by_cat:
                path = self._shard_path(cat)
                if path.exists():
                    self._save_shard(cat, [])

        for cat, cat_entries in by_cat.items():
            self._save_shard(cat, cat_entries)

    def _save_shard(self, category: str, entries: list[LTMEntry]) -> None:
        """将指定 category 的条目写入对应分片文件（加写锁）。"""
        path = self._shard_path(category)
        try:
            with self._lock_for(path):
                metadata = {
                    "category": category,
                    "entries": [asdict(e) for e in entries],
                    "last_updated": _now_iso(),
                    "entry_count": len(entries),
                }
                post = frontmatter.Post("", **metadata)
                path.write_text(frontmatter.dumps(post), encoding="utf-8")
        except OSError as exc:
            raise LTMError(f"Failed to save shard '{category}': {exc}") from exc

    def _relevance_score(self, entry: LTMEntry, query_token: str) -> int:
        """
        Simple relevance scoring for keyword search.
        关键词搜索的简单相关性评分。

        Scoring:
          +3  content 完全包含 query
          +2  任意 tag 包含 query
          +1  category 包含 query
        """
        score = 0
        if _contains_query(entry.content, query_token):
            score += 3
        if any(_contains_query(tag, query_token) for tag in entry.tags):
            score += 2
        if _contains_query(entry.category, query_token):
            score += 1
        return score

    def _get_weight_multipliers(self, entries: list[LTMEntry]) -> list[float]:
        """
        返回每个条目的权重乘数（1.0 ~ 1.4），懒加载 MemoryWeight。
        权重范围 1-5，对应乘数 1.0 / 1.1 / 1.2 / 1.3 / 1.4。
        用于在 BM25/关键词分数上叠加重要性加成。

        Args:
            entries: LTMEntry 列表。

        Returns:
            与 entries 等长的 float 列表（乘数）。
        """
        try:
            from core.weight import MemoryWeight
            mw = MemoryWeight(self._memory_dir)
            # 权重 1→1.0，2→1.1，3→1.2，4→1.3，5→1.4
            return [1.0 + (mw.get_weight(e.id) - 1) * 0.1 for e in entries]
        except Exception:
            # MemoryWeight 不可用时降级：全部乘数为 1.0（不影响检索行为）
            return [1.0] * len(entries)

    def _sort_by_weight(self, entries: list[LTMEntry]) -> list[LTMEntry]:
        """
        无查询词时，仅按权重降序排列条目。
        权重相同时保持原始顺序（stable sort）。

        Args:
            entries: LTMEntry 列表。

        Returns:
            按权重降序排列的 LTMEntry 列表。
        """
        try:
            from core.weight import MemoryWeight
            mw = MemoryWeight(self._memory_dir)
            # stable sort：权重相同时保持原始顺序
            return sorted(entries, key=lambda e: mw.get_weight(e.id), reverse=True)
        except Exception:
            return entries

    def _sync_to_vector_store(self, entry: LTMEntry) -> None:
        """
        同步记忆条目到向量存储（v1.6.0）
        
        Args:
            entry: LTMEntry 记忆条目
        """
        if not self._vector_store or not self._vector_store.semantic_enabled:
            return
        
        import logging
        _logger = logging.getLogger(__name__)
        
        try:
            # 构建用于语义搜索的文本（内容 + 标签）
            searchable_text = f"{entry.content} {' '.join(entry.tags)}"
            
            # 异步批量添加（加入缓存）
            self._vector_store.add(
                entry_id=entry.id,
                content=searchable_text,
                metadata={
                    "category": entry.category,
                    "tags": entry.tags,
                    "source": entry.source,
                    "timestamp": entry.created_at,
                },
                flush=False,  # 批量处理
            )
        except Exception as e:
            _logger.warning(f"Failed to sync to vector store: {e}")
            # 非阻塞错误，继续执行
    
    def flush_vector_store(self) -> None:
        """刷新向量存储批量缓存（v1.6.0）"""
        if self._vector_store and self._vector_store.semantic_enabled:
            import logging
            _logger = logging.getLogger(__name__)
            try:
                self._vector_store.flush()
                _logger.debug("Vector store flushed")
            except Exception as e:
                _logger.warning(f"Failed to flush vector store: {e}")

    def _hybrid_search(
        self,
        query: str,
        pool: list[LTMEntry],
        max_results: int,
        use_weight: bool,
        semantic_weight: float,
    ) -> list[LTMEntry]:
        """
        混合检索：BM25 + 语义搜索融合（v1.6.0）
        
        Args:
            query: 查询文本
            pool: 候选条目池
            max_results: 返回结果数
            use_weight: 是否使用权重加成
            semantic_weight: 语义分数权重
            
        Returns:
            融合排序后的 LTMEntry 列表
        """
        # 1. 执行 BM25 搜索获取初步结果
        query_tokens = _tokenize(query)
        keyword_scores = [
            sum(self._relevance_score(entry, tok) for tok in query_tokens)
            for entry in pool
        ]
        
        # 2. 构建 BM25 结果列表
        bm25_results = []
        if _BM25_AVAILABLE and len(pool) >= 1:
            corpus = [
                _tokenize(f"{e.content} {' '.join(e.tags)} {e.category}")
                for e in pool
            ]
            bm25 = _BM25Okapi(corpus)
            scores = bm25.get_scores(query_tokens)
            
            for i, entry in enumerate(pool):
                if scores[i] > 0 or keyword_scores[i] > 0:
                    bm25_results.append({
                        "id": entry.id,
                        "score": float(scores[i]) + keyword_scores[i],
                        "content": entry.content,
                        "metadata": {"entry": entry},
                    })
        else:
            # Fallback
            for i, entry in enumerate(pool):
                if keyword_scores[i] > 0:
                    bm25_results.append({
                        "id": entry.id,
                        "score": keyword_scores[i],
                        "content": entry.content,
                        "metadata": {"entry": entry},
                    })
        
        # 3. 语义搜索融合
        hybrid_results = self._vector_store.hybrid_search(
            query=query,
            bm25_results=bm25_results,
            top_k=max_results,
            semantic_weight=semantic_weight,
        )
        
        # 4. 提取条目并应用权重加成
        result_entries = []
        for r in hybrid_results:
            entry = r.metadata.get("entry") if r.metadata else None
            if entry:
                result_entries.append((r.score, entry))
        
        # 5. 应用 MemoryWeight 加成
        if use_weight:
            weight_multipliers = self._get_weight_multipliers([e for _, e in result_entries])
            boosted = []
            for i, (score, entry) in enumerate(result_entries):
                w_mult = weight_multipliers[i] if weight_multipliers else 1.0
                boosted.append((score * w_mult, entry))
            result_entries = boosted
        
        # 6. 排序返回
        result_entries.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in result_entries[:max_results]]



# ─────────────────────────────────────────────────────────────────────────────
# Null Lock (filelock not installed fallback)
# ─────────────────────────────────────────────────────────────────────────────

class _NullLock:
    """无操作锁，filelock 未安装时的降级方案。"""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


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
        similar_to=d.get("similar_to"),  # 支持读取 similar_to 字段
    )


def _entry_to_summary(entry: LTMEntry) -> dict:
    return {
        "id":         entry.id,
        "content":    entry.content,
        "tags":       entry.tags,
        "created_at": entry.created_at,
    }

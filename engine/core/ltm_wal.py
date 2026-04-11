"""
core/ltm_wal.py — WAL-enhanced Long-Term Memory Manager

增强版 LTMManager，集成 Write-Ahead Log 增量写入机制。
完全兼容原 LTMManager API，自动切换 WAL 模式。

使用方式:
    from core.ltm_wal import LTMManagerWAL as LTMManager
    
    # 用法与原有 LTMManager 完全相同
    ltm = LTMManagerWAL(memory_dir)
    entry = ltm.save(content="...", category="preference")

性能特点:
    - 新增条目: O(1) 追加到 WAL，无需重写整个文件
    - 读取条目: 自动合并主文件 + WAL 日志
    - 后台合并: 定时/阈值触发，不影响用户体验
    - 故障恢复: WAL 日志可重放，数据不丢失

配置选项:
    - enable_wal: 是否启用 WAL (默认 True)
    - wal_merge_threshold: 合并阈值 (默认 100)
    - wal_merge_interval: 后台合并间隔秒数 (默认 300)
    - wal_max_size: 单个 WAL 文件最大大小 (默认 10MB)
"""

import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.wal import WALManager

from core.ltm import (
    LTMEntry, LTMError, _now_iso, asdict,
    VALID_CATEGORIES, _contains_query,
    _FileLock, _FILELOCK_AVAILABLE, _NullLock,
    _load_frontmatter_file, frontmatter,
    Encryptor, SensitiveDetector,
)

logger = logging.getLogger(__name__)


class LTMManagerWAL:
    """
    WAL-enhanced Long-Term Memory Manager
    
    API 完全兼容原 LTMManager，内部使用 WAL 增量写入。
    """
    
    _LTM_FILENAME = "long-term-memory.md"
    _SHARD_PREFIX = "long-term-memory-"
    _SHARD_SUFFIX = ".md"
    
    def __init__(
        self,
        memory_dir: Path,
        encryptor: Optional[Encryptor] = None,
        detector: Optional[SensitiveDetector] = None,
        enable_wal: bool = True,
        wal_merge_threshold: int = 100,
        wal_merge_interval: int = 300,
        wal_max_size: int = 10 * 1024 * 1024,  # 10MB
    ) -> None:
        """
        初始化 WAL 增强版 LTMManager
        
        Args:
            memory_dir: 记忆库根目录
            encryptor: 加密器实例 (可选)
            detector: 敏感信息检测器 (可选)
            enable_wal: 是否启用 WAL 增量写入 (默认 True)
            wal_merge_threshold: WAL 合并阈值 (默认 100)
            wal_merge_interval: 后台合并间隔秒数 (默认 300)
            wal_max_size: 单个 WAL 文件最大大小 (默认 10MB)
        """
        self._memory_dir = Path(memory_dir)
        self._ltm_path = self._memory_dir / self._LTM_FILENAME
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        
        secure_dir = self._memory_dir / "secure"
        self._encryptor = encryptor or Encryptor(secure_dir)
        self._detector = detector or SensitiveDetector()
        
        # WAL 配置
        self.enable_wal = enable_wal
        self.wal_merge_threshold = wal_merge_threshold
        self.wal_merge_interval = wal_merge_interval
        self.wal_max_size = wal_max_size
        
        # 延迟导入 WALManager，避免循环依赖
        self._wal_manager: Optional["WALManager"] = None
        
        # 首次初始化时迁移旧数据
        self._migrate_legacy_file()
        
        # 如果启用 WAL，初始化 WALManager
        if self.enable_wal:
            self._init_wal_manager()
        
        # 初始化语义向量存储（v1.6.0）
        self._vector_store: Optional[Any] = None
        self._init_vector_store()
    
    def _init_vector_store(self) -> None:
        """初始化语义向量存储（可选，失败不阻塞）"""
        try:
            from core.vector_store import SemanticVectorStore
            vector_dir = self._memory_dir / "vectors"
            self._vector_store = SemanticVectorStore(vector_dir)
            logger.info("Vector store initialized for semantic search (WAL mode)")
        except Exception as e:
            logger.warning(f"Vector store init failed: {e}, semantic search disabled")
            self._vector_store = None
    
    def _init_wal_manager(self) -> None:
        """初始化 WALManager"""
        try:
            from core.wal import WALManager as WM
            self._wal_manager = WM(
                memory_dir=self._memory_dir,
                max_wal_size=self.wal_max_size,
                merge_threshold=self.wal_merge_threshold,
                merge_interval=self.wal_merge_interval,
                enable_background_merge=True,
            )
            logger.info("WALManager initialized (incremental writes enabled)")
        except ImportError as e:
            logger.warning(f"Cannot import WALManager: {e}. Falling back to traditional writes.")
            self.enable_wal = False
        except Exception as e:
            logger.error(f"Failed to initialize WALManager: {e}. Falling back to traditional writes.")
            self.enable_wal = False
    
    # ── 兼容原 LTMManager 的公共接口 ────────────────────────────────────────────
    
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
        保存新条目到长期记忆 (WAL 增强版)
        
        如果启用 WAL，使用增量写入；否则回退到传统方式。
        """
        # 参数验证和敏感信息检测与原始相同
        if not content or not content.strip():
            raise ValueError("content must not be empty.")
        if category not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}.")
        
        if sensitive is None:
            sensitive = self._detector.is_sensitive(content)
        
        # 处理加密 (与原始相同)
        from core.ltm import Encryptor as LTMEncryptor
        resolved_passphrase = LTMEncryptor.get_passphrase(explicit=passphrase)
        
        # 如果需要 WAL 支持且已初始化
        if self.enable_wal and self._wal_manager:
            return self._save_with_wal(
                content=content,
                category=category,
                source=source,
                tags=tags or [],
                sensitive=sensitive,
                resolved_passphrase=resolved_passphrase,
            )
        else:
            # 回退到传统保存方式
            return self._save_traditional(
                content=content,
                category=category,
                source=source,
                tags=tags or [],
                sensitive=sensitive,
                resolved_passphrase=resolved_passphrase,
            )
    
    def _save_with_wal(
        self,
        content: str,
        category: str,
        source: str,
        tags: list[str],
        sensitive: bool,
        resolved_passphrase: Optional[str],
    ) -> LTMEntry:
        """
        使用 WAL 增量写入保存条目
        """
        import uuid
        from core.ltm import _dict_to_entry
        
        # 1. 去重检查 (与原始相同)
        existing_entries = self._load_shard(category)
        similar_to_id = None
        
        try:
            from core.deduplicator import Deduplicator
            dedup = Deduplicator(similarity_threshold=0.85, method="cosine")
            existing_contents = [e.content for e in existing_entries]
            
            if dedup.is_duplicate(content, existing_contents):
                duplicates = dedup.find_duplicates(content, existing_contents)
                if duplicates:
                    best_match = duplicates[0]
                    match_index = best_match["index"]
                    if 0 <= match_index < len(existing_entries):
                        similar_to_id = existing_entries[match_index].id
                        logger.debug(f"Found similar entry for content: {content[:50]}...")
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Deduplicator error (non-fatal): {e}")
        
        # 2. 处理敏感信息和加密
        encrypted_ref = None
        stored_content = content
        
        if sensitive:
            if not resolved_passphrase:
                stored_content = self._detector.redact(content)
            else:
                encrypted_ref = self._encryptor.encrypt(
                    key=f"ltm_{uuid.uuid4().hex[:8]}",
                    plaintext=content,
                    passphrase=resolved_passphrase,
                    category=category,
                )
                stored_content = self._detector.redact(content)
        
        # 3. 创建新条目
        from core.ltm import LTMEntry as OriginalLTMEntry
        entry = OriginalLTMEntry(
            id=str(uuid.uuid4()),
            content=stored_content,
            category=category,
            source=source,
            tags=tags,
            created_at=_now_iso(),
            updated_at=_now_iso(),
            sensitive=sensitive,
            encrypted_ref=encrypted_ref,
            similar_to=similar_to_id,
        )
        
        # 4. 使用 WAL 增量写入
        if self._wal_manager:
            self._wal_manager.append_entry(category, entry)
            
            # 如果 WAL 太大，触发异步合并
            if self._wal_manager._should_merge(category):
                # 后台合并，不阻塞用户操作
                import threading
                def merge_in_background():
                    try:
                        self._wal_manager.merge_wal(category, background=True)
                    except Exception as e:
                        logger.error(f"Background merge failed: {e}")
                
                threading.Thread(target=merge_in_background, daemon=True).start()
        
        # 5. 同步到向量存储（v1.6.0）
        self._sync_to_vector_store(entry)
        
        return entry
    
    def _save_traditional(
        self,
        content: str,
        category: str,
        source: str,
        tags: list[str],
        sensitive: bool,
        resolved_passphrase: Optional[str],
    ) -> LTMEntry:
        """
        传统保存方式 (回退)
        """
        # 导入原始 LTMManager 的保存逻辑
        from core.ltm import LTMManager as OriginalLTMManager
        
        # 创建临时原始管理器
        original_ltm = OriginalLTMManager(
            memory_dir=self._memory_dir,
            encryptor=self._encryptor,
            detector=self._detector,
        )
        
        # 使用原始保存方法
        return original_ltm.save(
            content=content,
            category=category,
            source=source,
            tags=tags,
            sensitive=sensitive,
            passphrase=resolved_passphrase,
        )
    
    def get(self, entry_id: str) -> Optional[LTMEntry]:
        """按 ID 获取单条记忆 (支持 WAL)"""
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
        搜索记忆条目 (支持 WAL + 权重加成 + 语义搜索 v1.6.0)

        与 ltm.py LTMManager.search() 行为完全一致，增加 WAL 读取支持和语义搜索。

        Args:
            query:       搜索关键词。
            category:    可选分类过滤。
            max_results: 最多返回条数。
            use_weight:  是否应用 MemoryWeight 权重加成（默认 True）。
            use_semantic: 是否启用语义搜索（默认 False）。
            semantic_weight: 语义分数权重，0-1（默认 0.6）。

        Returns:
            匹配的 LTMEntry 列表，按相关性 × 权重降序排列。
        """
        from core.ltm import _tokenize, _BM25_AVAILABLE, _BM25Okapi

        # 获取所有条目（已应用 WAL 合并）
        pool = self._load_shard(category) if category else self._load_entries()
        if not pool:
            return []
        if not query or not query.strip():
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
            for entry in pool
        ]

        # BM25 搜索
        if _BM25_AVAILABLE and len(pool) >= 1:
            corpus = [
                _tokenize(f"{e.content} {' '.join(e.tags)} {e.category}")
                for e in pool
            ]
            bm25 = _BM25Okapi(corpus)
            scores = bm25.get_scores(query_tokens)

            for i, entry in enumerate(pool):
                if any(_contains_query(tag, token) for tag in entry.tags for token in query_tokens):
                    scores[i] += 0.5

            # 权重加成（v1.5.0）
            weight_multipliers = self._get_weight_multipliers(pool) if use_weight else None

            combined: list[tuple[float, float, float, int, LTMEntry]] = []
            for i, entry in enumerate(pool):
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
        weight_multipliers = self._get_weight_multipliers(pool) if use_weight else None
        results = []
        for i in range(len(pool)):
            if keyword_scores[i] > 0:
                w_mult = weight_multipliers[i] if weight_multipliers else 1.0
                results.append((keyword_scores[i] * w_mult, pool[i]))
        results.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in results[:max_results]]

    def recall(self, query: str, max_results: int = 20) -> list[LTMEntry]:
        """search() 的别名，保持 API 兼容性。"""
        return self.search(query=query, max_results=max_results)

    def _get_weight_multipliers(self, entries: list[LTMEntry]) -> list[float]:
        """
        返回每个条目的权重乘数（1.0 ~ 1.4），懒加载 MemoryWeight。
        与 ltm.py 中的实现完全相同。
        """
        try:
            from core.weight import MemoryWeight
            mw = MemoryWeight(self._memory_dir)
            return [1.0 + (mw.get_weight(e.id) - 1) * 0.1 for e in entries]
        except Exception:
            return [1.0] * len(entries)

    def _sort_by_weight(self, entries: list[LTMEntry]) -> list[LTMEntry]:
        """无查询词时，仅按权重降序排列条目。"""
        try:
            from core.weight import MemoryWeight
            mw = MemoryWeight(self._memory_dir)
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
            logger.warning(f"Failed to sync to vector store: {e}")
            # 非阻塞错误，继续执行
    
    def flush_vector_store(self) -> None:
        """刷新向量存储批量缓存（v1.6.0）"""
        if self._vector_store and self._vector_store.semantic_enabled:
            try:
                self._vector_store.flush()
                logger.debug("Vector store flushed")
            except Exception as e:
                logger.warning(f"Failed to flush vector store: {e}")
    
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
        from core.ltm import _tokenize, _BM25_AVAILABLE, _BM25Okapi
        
        # 1. 执行 BM25 搜索获取初步结果
        query_tokens = _tokenize(query)
        
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
    
    def update(
        self,
        entry_id: str,
        content: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
    ) -> LTMEntry:
        """更新条目 (支持 WAL)"""
        # 先找到条目
        entry = self.get(entry_id)
        if not entry:
            raise LTMError(f"Entry '{entry_id}' not found.")
        
        # 构建更新字典
        updates = {}
        if content is not None:
            updates["content"] = content
        if tags is not None:
            updates["tags"] = tags
        if category is not None:
            if category not in VALID_CATEGORIES:
                raise ValueError(f"category must be one of {VALID_CATEGORIES}.")
            updates["category"] = category
        
        # 如果启用 WAL，使用增量更新
        if self.enable_wal and self._wal_manager:
            old_category = entry.category
            new_category = category or old_category
            
            if old_category != new_category:
                # 分类变化：删除旧分类，新增到新分类
                self._wal_manager.delete_entry(old_category, entry_id)
                
                # 创建新条目
                new_entry = LTMEntry(
                    id=entry_id,
                    content=content or entry.content,
                    category=new_category,
                    source=entry.source,
                    tags=tags or entry.tags,
                    created_at=entry.created_at,
                    updated_at=_now_iso(),
                    sensitive=entry.sensitive,
                    encrypted_ref=entry.encrypted_ref,
                    similar_to=entry.similar_to,
                )
                self._wal_manager.append_entry(new_category, new_entry)
                
                # 触发合并检查
                if self._wal_manager._should_merge(new_category):
                    self._wal_manager.merge_wal(new_category, background=True)
                
                return new_entry
            else:
                # 同分类更新
                self._wal_manager.update_entry(entry.category, entry_id, updates)
                
                # 更新本地副本
                if content is not None:
                    entry.content = content
                if tags is not None:
                    entry.tags = tags
                entry.updated_at = _now_iso()
                
                return entry
        else:
            # 回退到传统更新
            from core.ltm import LTMManager as OriginalLTMManager
            original_ltm = OriginalLTMManager(
                memory_dir=self._memory_dir,
                encryptor=self._encryptor,
                detector=self._detector,
            )
            return original_ltm.update(entry_id, content, tags, category)
    
    def delete(self, entry_id: str, confirm: bool = False) -> bool:
        """删除条目 (支持 WAL)"""
        if not confirm:
            raise ValueError(
                "Deletion requires confirm=True. "
                "This is a safety guard to prevent accidental deletion."
            )
        
        # 先找到条目
        entry = self.get(entry_id)
        if not entry:
            return False
        
        # 如果启用 WAL，使用增量删除
        if self.enable_wal and self._wal_manager:
            self._wal_manager.delete_entry(entry.category, entry_id)
            return True
        else:
            # 回退到传统删除
            from core.ltm import LTMManager as OriginalLTMManager
            original_ltm = OriginalLTMManager(
                memory_dir=self._memory_dir,
                encryptor=self._encryptor,
                detector=self._detector,
            )
            return original_ltm.delete(entry_id, confirm=True)
    
    def load_profile(self) -> dict:
        """加载用户档案 (支持 WAL)"""
        entries = self._load_entries()
        
        profile_entries = [e for e in entries if e.category == "profile"]
        preference_entries = [e for e in entries if e.category == "preference"]
        project_entries = [e for e in entries if e.category == "project"]
        decision_entries = [e for e in entries if e.category == "decision"]
        habit_entries = [e for e in entries if e.category == "habit"]
        
        return {
            "profile": [self._entry_to_summary(e) for e in profile_entries],
            "preferences": [self._entry_to_summary(e) for e in preference_entries],
            "active_projects": [self._entry_to_summary(e) for e in project_entries],
            "recent_decisions": [self._entry_to_summary(e) for e in decision_entries[-5:]],
            "habits": [self._entry_to_summary(e) for e in habit_entries],
            "total_entries": len(entries),
        }
    
    def list_all(
        self,
        category: str | None = None,
        limit: int = 100,
    ) -> list[LTMEntry]:
        """列出所有条目 (支持 WAL)"""
        entries = self._load_entries()
        if category:
            entries = [e for e in entries if e.category == category]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]
    
    # ── 私有助手方法 ────────────────────────────────────────────────────────────
    
    def _shard_path(self, category: str) -> Path:
        """返回指定 category 对应的分片文件路径。"""
        import re
        safe_cat = re.sub(r"[^\w-]", "_", category)
        return self._memory_dir / f"{self._SHARD_PREFIX}{safe_cat}{self._SHARD_SUFFIX}"
    
    def _lock_for(self, path: Path):
        """返回指定文件的锁"""
        if _FILELOCK_AVAILABLE:
            return _FileLock(str(path) + ".lock", timeout=30)
        return _NullLock()
    
    def _migrate_legacy_file(self) -> None:
        """迁移旧版单文件数据到分片 (与原始相同)"""
        if not self._ltm_path.exists():
            return
        migrated_path = self._memory_dir / "long-term-memory.migrated.md"
        if migrated_path.exists():
            return
        
        try:
            post = _load_frontmatter_file(self._ltm_path)
            raw_entries = post.metadata.get("entries", [])
            if not isinstance(raw_entries, list) or not raw_entries:
                self._ltm_path.rename(migrated_path)
                return
            
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
                    self._save_shard_traditional(cat, existing + new_entries)
            
            self._ltm_path.rename(migrated_path)
        except Exception as exc:
            logger.warning(f"LTM 旧文件迁移失败：{exc}", exc_info=True)
    
    def _load_entries(self, category: Optional[str] = None) -> list[LTMEntry]:
        """加载条目 (支持 WAL)"""
        if category:
            return self._load_shard(category)
        
        all_entries: list[LTMEntry] = []
        for cat in VALID_CATEGORIES:
            all_entries.extend(self._load_shard(cat))
        return all_entries
    
    def _load_shard(self, category: str) -> list[LTMEntry]:
        """加载分片条目 (自动合并 WAL)"""
        # 1. 加载主文件条目
        path = self._shard_path(category)
        main_entries: list[LTMEntry] = []
        
        if path.exists():
            try:
                with self._lock_for(path):
                    post = _load_frontmatter_file(path)
                raw_entries = post.metadata.get("entries", [])
                if isinstance(raw_entries, list):
                    main_entries = [_dict_to_entry(e) for e in raw_entries if isinstance(e, dict)]
            except Exception:
                main_entries = []
        
        # 2. 如果启用 WAL，合并 WAL 日志
        if self.enable_wal and self._wal_manager:
            return self._wal_manager.apply_wal_to_entries(category, main_entries)
        
        return main_entries
    
    def _save_shard_traditional(self, category: str, entries: list[LTMEntry]) -> None:
        """传统保存分片 (用于迁移和回退)"""
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
    
    def _entry_to_summary(self, entry: LTMEntry) -> dict:
        """条目摘要转换"""
        return {
            "id": entry.id,
            "content": entry.content,
            "tags": entry.tags,
            "created_at": entry.created_at,
        }
    
    def get_wal_stats(self) -> dict:
        """获取 WAL 统计信息"""
        if self.enable_wal and self._wal_manager:
            return self._wal_manager.get_stats()
        return {"enabled": False, "message": "WAL not enabled or not initialized"}
    
    def force_wal_merge(self, category: Optional[str] = None) -> dict:
        """
        强制合并 WAL 日志
        
        Args:
            category: 可选，指定分类；为 None 时合并所有分类
            
        Returns:
            合并结果统计
        """
        if not self.enable_wal or not self._wal_manager:
            return {"success": False, "message": "WAL not enabled"}
        
        results = {}
        categories_to_merge = [category] if category else VALID_CATEGORIES
        
        for cat in categories_to_merge:
            try:
                success = self._wal_manager.merge_wal(cat, background=False)
                results[cat] = {
                    "success": success,
                    "message": "Merged successfully" if success else "Merge failed"
                }
            except Exception as e:
                results[cat] = {
                    "success": False,
                    "message": f"Error: {str(e)}"
                }
        
        return {
            "success": all(r["success"] for r in results.values() if r),
            "results": results
        }


def _dict_to_entry(d: dict) -> LTMEntry:
    """字典转 LTMEntry (从 ltm.py 导入)"""
    import uuid
    from core.ltm import LTMEntry as OriginalLTMEntry, _now_iso as ltm_now_iso
    
    return OriginalLTMEntry(
        id=d.get("id", str(uuid.uuid4())),
        content=d.get("content", ""),
        category=d.get("category", "other"),
        source=d.get("source", "user-explicit"),
        tags=d.get("tags", []),
        created_at=d.get("created_at", ltm_now_iso()),
        updated_at=d.get("updated_at", ltm_now_iso()),
        sensitive=d.get("sensitive", False),
        encrypted_ref=d.get("encrypted_ref"),
        similar_to=d.get("similar_to"),
    )
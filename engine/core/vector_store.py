"""
Vector Store — 语义检索模块（基于 sentence-transformers + ChromaDB）

提供基于深度学习的语义搜索能力，支持模糊语义匹配。

版本: 3.0 (语义搜索版)
"""

import os
import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果"""
    entry_id: str
    score: float
    content: str
    metadata: Dict[str, Any]
    source: str  # "bm25", "semantic", "hybrid"


class SemanticVectorStore:
    """
    语义向量存储 — 基于 sentence-transformers + ChromaDB
    
    特性:
    - 支持语义相似度检索（理解同义词、模糊查询）
    - 自动降级到 TF-IDF（当模型加载失败时）
    - 混合检索：BM25 + 语义分数融合
    - 批量处理优化
    """
    
    def __init__(
        self, 
        persist_dir: Path,
        collection_name: str = "memory_collection",
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        初始化语义向量存储
        
        Args:
            persist_dir: 持久化目录
            collection_name: ChromaDB集合名称
            embedding_model: sentence-transformers模型名
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model
        
        # 状态标记
        self.semantic_enabled = False
        self.chroma_available = False
        self.model = None
        self.collection = None
        
        # 批量缓存
        self._batch_buffer: List[Dict] = []
        self._batch_size = 10
        
        # 初始化
        self._init_store()
    
    def _init_store(self) -> None:
        """初始化存储（带降级机制）"""
        try:
            self._init_chroma()
            self._init_model()
            self.semantic_enabled = True
            logger.info(f"SemanticVectorStore initialized: model={self.embedding_model_name}")
        except Exception as e:
            logger.warning(f"Semantic store init failed: {e}, falling back to keyword search")
            self.semantic_enabled = False
            # 清理已初始化的资源
            self._cleanup_partial_init()
    
    def _cleanup_partial_init(self) -> None:
        """清理部分初始化失败的资源"""
        try:
            if hasattr(self, 'chroma_client') and self.chroma_client:
                # ChromaDB 需要重置内部状态
                try:
                    self.chroma_client.reset()
                except Exception:
                    pass
                import gc
                del self.chroma_client
                self.chroma_client = None
                self.collection = None
                gc.collect()
        except Exception:
            pass  # 忽略清理错误
    
    def close(self) -> None:
        """显式关闭资源（确保ChromaDB正确释放）"""
        try:
            # 刷新批量缓存
            if hasattr(self, '_batch_buffer') and self._batch_buffer:
                self.flush()
            # 强制垃圾回收释放文件句柄
            self._cleanup_partial_init()
        except Exception as e:
            logger.warning(f"Error closing vector store: {e}")
    
    def __enter__(self):
        """上下文管理器支持"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出时关闭资源"""
        self.close()
        return False
    
    def _init_chroma(self) -> None:
        """初始化 ChromaDB"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.persist_dir / "chroma_db"),
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            self.chroma_available = True
            logger.info("ChromaDB initialized")
        except ImportError:
            logger.warning("chromadb not installed, semantic search disabled")
            raise
        except Exception as e:
            logger.error(f"ChromaDB init failed: {e}")
            raise
    
    def _init_model(self) -> None:
        """初始化 embedding 模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            # 检查本地缓存
            cache_dir = self.persist_dir / "models"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            self.model = SentenceTransformer(
                self.embedding_model_name,
                cache_folder=str(cache_dir)
            )
            logger.info(f"Embedding model loaded: {self.embedding_model_name}")
        except ImportError:
            logger.warning("sentence_transformers not installed")
            raise
        except Exception as e:
            logger.error(f"Model loading failed: {e}")
            raise
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        """
        编码文本为向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        if not self.semantic_enabled or self.model is None:
            raise RuntimeError("Semantic search not available")
        
        # 批处理优化
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    def add(
        self, 
        entry_id: str, 
        content: str, 
        metadata: Optional[Dict] = None,
        flush: bool = True
    ) -> bool:
        """
        添加记忆到向量索引
        
        Args:
            entry_id: 条目ID
            content: 文本内容
            metadata: 元数据
            flush: 是否立即刷新（False则加入批量缓存）
            
        Returns:
            是否成功
        """
        if not self.semantic_enabled:
            logger.debug("Semantic search disabled, skipping vector add")
            return False
        
        try:
            item = {
                "id": entry_id,
                "content": content,
                "metadata": metadata or {}
            }
            
            if flush:
                # 立即处理
                self._flush_batch([item])
            else:
                # 加入批量缓存
                self._batch_buffer.append(item)
                if len(self._batch_buffer) >= self._batch_size:
                    self.flush()
            
            return True
        except Exception as e:
            logger.error(f"Failed to add vector: {e}")
            return False
    
    def _flush_batch(self, items: List[Dict]) -> None:
        """批量写入 ChromaDB"""
        if not items:
            return
        
        # 编码向量
        contents = [item["content"] for item in items]
        embeddings = self.encode(contents)
        
        # 写入 ChromaDB
        self.collection.add(
            embeddings=embeddings,
            documents=contents,
            metadatas=[item["metadata"] for item in items],
            ids=[item["id"] for item in items]
        )
        
        logger.debug(f"Flushed {len(items)} items to ChromaDB")
    
    def flush(self) -> None:
        """刷新批量缓存"""
        if self._batch_buffer:
            self._flush_batch(self._batch_buffer)
            self._batch_buffer = []
    
    def search(
        self, 
        query: str, 
        top_k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数
            filter: 过滤条件
            
        Returns:
            搜索结果列表
        """
        if not self.semantic_enabled:
            logger.warning("Semantic search not available")
            return []
        
        try:
            # 编码查询
            query_embedding = self.encode([query])[0]
            
            # ChromaDB 查询
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter
            )
            
            # 解析结果
            search_results = []
            for i, doc_id in enumerate(results.get("ids", [[]])[0]):
                if not doc_id:
                    continue
                
                distance = results.get("distances", [[]])[0][i]
                document = results.get("documents", [[]])[0][i]
                metadata = results.get("metadatas", [[]])[0][i]
                
                # 余弦距离转相似度分数 (0-1)
                score = 1.0 - min(distance, 1.0)
                
                search_results.append(SearchResult(
                    entry_id=doc_id,
                    score=score,
                    content=document,
                    metadata=metadata or {},
                    source="semantic"
                ))
            
            return search_results
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def hybrid_search(
        self,
        query: str,
        bm25_results: List[Dict],
        top_k: int = 5,
        semantic_weight: float = 0.6
    ) -> List[SearchResult]:
        """
        混合检索：BM25 + 语义分数融合
        
        Args:
            query: 查询文本
            bm25_results: BM25搜索结果 (含id, score, content)
            top_k: 返回结果数
            semantic_weight: 语义分数权重 (0-1)
            
        Returns:
            融合后的搜索结果
        """
        if not self.semantic_enabled:
            # 降级：返回BM25结果
            return [
                SearchResult(
                    entry_id=r.get("id", ""),
                    score=r.get("score", 0.0),
                    content=r.get("content", ""),
                    metadata=r.get("metadata", {}),
                    source="bm25"
                )
                for r in bm25_results[:top_k]
            ]
        
        try:
            # 获取语义搜索结果
            semantic_results = self.search(query, top_k=top_k * 2)
            
            # 归一化BM25分数
            if bm25_results:
                bm25_scores = [r.get("score", 0) for r in bm25_results]
                bm25_min, bm25_max = min(bm25_scores), max(bm25_scores)
                bm25_range = bm25_max - bm25_min if bm25_max > bm25_min else 1.0
            else:
                bm25_min, bm25_range = 0, 1.0
            
            # 合并结果
            combined: Dict[str, SearchResult] = {}
            
            # 添加BM25结果（已归一化）
            for r in bm25_results:
                entry_id = r.get("id", "")
                if not entry_id:
                    continue
                
                normalized_score = (r.get("score", 0) - bm25_min) / bm25_range
                combined[entry_id] = SearchResult(
                    entry_id=entry_id,
                    score=normalized_score * (1 - semantic_weight),
                    content=r.get("content", ""),
                    metadata=r.get("metadata", {}),
                    source="bm25"
                )
            
            # 添加语义结果（已归一化，余弦相似度天然0-1）
            for r in semantic_results:
                if r.entry_id in combined:
                    # 已存在，加权融合
                    existing = combined[r.entry_id]
                    bm25_part = existing.score  # 已经是 (1-w) * bm25
                    semantic_part = r.score * semantic_weight
                    
                    combined[r.entry_id] = SearchResult(
                        entry_id=r.entry_id,
                        score=bm25_part + semantic_part,
                        content=r.content,
                        metadata=r.metadata,
                        source="hybrid"
                    )
                else:
                    # 新结果
                    combined[r.entry_id] = SearchResult(
                        entry_id=r.entry_id,
                        score=r.score * semantic_weight,
                        content=r.content,
                        metadata=r.metadata,
                        source="semantic"
                    )
            
            # 排序并返回
            results = sorted(combined.values(), key=lambda x: x.score, reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {e}, falling back to BM25")
            return [
                SearchResult(
                    entry_id=r.get("id", ""),
                    score=r.get("score", 0.0),
                    content=r.get("content", ""),
                    metadata=r.get("metadata", {}),
                    source="bm25"
                )
                for r in bm25_results[:top_k]
            ]
    
    def delete(self, entry_id: str) -> bool:
        """
        删除指定向量
        
        Args:
            entry_id: 条目ID
            
        Returns:
            是否成功
        """
        if not self.semantic_enabled:
            return False
        
        try:
            self.collection.delete(ids=[entry_id])
            logger.debug(f"Deleted vector: {entry_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vector {entry_id}: {e}")
            return False
    
    def update(
        self, 
        entry_id: str, 
        content: str, 
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        更新向量
        
        Args:
            entry_id: 条目ID
            content: 新内容
            metadata: 新元数据
            
        Returns:
            是否成功
        """
        # 先删除再添加
        if self.delete(entry_id):
            return self.add(entry_id, content, metadata, flush=True)
        return False
    
    def get_count(self) -> int:
        """
        获取向量总数
        
        Returns:
            向量数量
        """
        if not self.semantic_enabled:
            return 0
        try:
            return self.collection.count()
        except:
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计字典
        """
        return {
            "semantic_enabled": self.semantic_enabled,
            "chroma_available": self.chroma_available,
            "model": self.embedding_model_name if self.semantic_enabled else None,
            "vector_count": self.get_count(),
            "persist_dir": str(self.persist_dir)
        }


# 兼容性：保留旧类名
VectorStore = SemanticVectorStore

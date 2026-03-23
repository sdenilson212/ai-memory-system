"""
Vector Store — 向量检索模块
支持语义搜索，补充关键词检索
版本: 1.0
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class VectorStore:
    """
    向量检索模块提供语义搜索能力，基于文本 embedding 相似度进行检索。
    
    注意：这是一个轻量级实现，完整版本需要安装 chromadb 和 sentence-transformers。
    当前版本使用简单的 TF-IDF 向量作为替代。
    """
    
    def __init__(self, persist_dir: Path) -> None:
        """
        初始化向量存储
        
        Args:
            persist_dir: 用于持久化存储的目录路径
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        # 存储结构
        self.vectors_file = self.persist_dir / "vectors.json"
        self.metadata_file = self.persist_dir / "metadata.json"
        
        # 内存存储
        self.vectors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        
        # 词汇表（用于 TF-IDF 简化版）
        self.vocabulary: Dict[str, int] = {}
        self.vocab_file = self.persist_dir / "vocabulary.json"
        
        self._load_from_disk()
    
    def _load_from_disk(self) -> None:
        """从磁盘加载数据"""
        try:
            if self.vectors_file.exists():
                with open(self.vectors_file, 'r', encoding='utf-8') as f:
                    self.vectors = json.load(f)
            
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            
            if self.vocab_file.exists():
                with open(self.vocab_file, 'r', encoding='utf-8') as f:
                    self.vocabulary = json.load(f)
            
            logger.info(f"VectorStore loaded: {len(self.vectors)} vectors, vocab size: {len(self.vocabulary)}")
        except Exception as e:
            logger.warning(f"Failed to load VectorStore: {e}, starting fresh")
    
    def _save_to_disk(self) -> None:
        """保存数据到磁盘"""
        try:
            with open(self.vectors_file, 'w', encoding='utf-8') as f:
                json.dump(self.vectors, f, ensure_ascii=False, indent=2)
            
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
            
            with open(self.vocab_file, 'w', encoding='utf-8') as f:
                json.dump(self.vocabulary, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save VectorStore: {e}")
    
    def _update_vocabulary(self, content: str) -> None:
        """更新词汇表"""
        # 简单的分词
        words = content.lower().split()
        for word in words:
            if word not in self.vocabulary:
                self.vocabulary[word] = len(self.vocabulary)
    
    def _content_to_vector(self, content: str) -> List[float]:
        """将文本内容转换为向量（简化版 TF-IDF）"""
        if not content:
            return []
        
        # 确保词汇表最新
        self._update_vocabulary(content)
        
        # 初始化向量
        vector = [0.0] * len(self.vocabulary)
        
        # 统计词频
        words = content.lower().split()
        word_count = {}
        for word in words:
            word_count[word] = word_count.get(word, 0) + 1
        
        # 填充向量
        for word, count in word_count.items():
            if word in self.vocabulary:
                idx = self.vocabulary[word]
                vector[idx] = count
        
        # 归一化
        import math
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        
        return vector
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        # 对齐向量长度
        max_len = max(len(vec1), len(vec2))
        vec1_ext = vec1 + [0.0] * (max_len - len(vec1))
        vec2_ext = vec2 + [0.0] * (max_len - len(vec2))
        
        # 点积
        import math
        dot_product = sum(a * b for a, b in zip(vec1_ext, vec2_ext))
        norm1 = math.sqrt(sum(a * a for a in vec1_ext))
        norm2 = math.sqrt(sum(b * b for b in vec2_ext))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return max(0.0, min(1.0, similarity))
    
    def add(self, entry_id: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """
        添加向量到索引
        
        Args:
            entry_id: 条目ID
            content: 文本内容
            metadata: 元数据
            
        Returns:
            是否成功
        """
        try:
            vector = self._content_to_vector(content)
            self.vectors[entry_id] = vector
            
            self.metadata[entry_id] = {
                "content": content,
                "metadata": metadata or {},
                "timestamp": metadata.get("timestamp") if metadata else None
            }
            
            self._save_to_disk()
            logger.debug(f"Added vector for entry_id: {entry_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add vector for {entry_id}: {e}")
            return False
    
    def search(self, query: str, top_k: int = 5, filter: Optional[Dict] = None) -> List[Dict]:
        """
        语义搜索，返回最相似的 top_k 条
        
        Args:
            query: 查询文本
            top_k: 返回结果数
            filter: 过滤条件（暂未实现）
            
        Returns:
            搜索结果列表，每个元素包含 entry_id, score, content 等
        """
        try:
            query_vector = self._content_to_vector(query)
            
            # 计算相似度
            results = []
            for entry_id, vector in self.vectors.items():
                similarity = self._cosine_similarity(query_vector, vector)
                
                # 检查元数据
                meta = self.metadata.get(entry_id, {})
                
                results.append({
                    "entry_id": entry_id,
                    "score": similarity,
                    "content": meta.get("content", ""),
                    "metadata": meta.get("metadata", {})
                })
            
            # 按相似度降序排序
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # 过滤低分结果（阈值 0.1）
            results = [r for r in results if r["score"] >= 0.1]
            
            return results[:top_k]
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return []
    
    def delete(self, entry_id: str) -> bool:
        """
        删除指定向量
        
        Args:
            entry_id: 要删除的条目ID
            
        Returns:
            是否成功
        """
        try:
            if entry_id in self.vectors:
                del self.vectors[entry_id]
            
            if entry_id in self.metadata:
                del self.metadata[entry_id]
            
            self._save_to_disk()
            logger.debug(f"Deleted vector for entry_id: {entry_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete vector {entry_id}: {e}")
            return False
    
    def update(self, entry_id: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """
        更新向量
        
        Args:
            entry_id: 条目ID
            content: 新内容
            metadata: 新元数据
            
        Returns:
            是否成功
        """
        # 先删除，再添加
        if self.delete(entry_id):
            return self.add(entry_id, content, metadata)
        return False
    
    def get_count(self) -> int:
        """
        返回向量总数
        
        Returns:
            向量总数
        """
        return len(self.vectors)
    
    def hybrid_search(self, query: str, keyword_results: List[Dict], top_k: int = 5) -> List[Dict]:
        """
        混合检索：结合关键词结果和向量结果
        
        Args:
            query: 查询文本
            keyword_results: 关键词搜索结果
            top_k: 返回结果数
            
        Returns:
            合并排序后的结果
        """
        # 向量检索
        vector_results = self.search(query, top_k=top_k * 2)
        
        # 合并结果
        combined = {}
        
        # 添加关键词结果（给较高的基础分）
        for idx, result in enumerate(keyword_results):
            entry_id = result.get("id") or f"keyword_{idx}"
            combined[entry_id] = {
                "entry_id": entry_id,
                "score": 0.8 - (idx * 0.1),  # 递减分数
                "content": result.get("content", ""),
                "metadata": result.get("metadata", {}),
                "source": "keyword"
            }
        
        # 添加向量结果
        for result in vector_results:
            entry_id = result["entry_id"]
            if entry_id in combined:
                # 合并分数（加权平均）
                combined[entry_id]["score"] = (combined[entry_id]["score"] + result["score"]) / 2
                combined[entry_id]["source"] = "both"
            else:
                combined[entry_id] = result
                combined[entry_id]["source"] = "vector"
        
        # 转换回列表并排序
        combined_list = list(combined.values())
        combined_list.sort(key=lambda x: x["score"], reverse=True)
        
        return combined_list[:top_k]

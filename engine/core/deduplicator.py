"""
Deduplicator — 自动去重模块
检测相似内容，避免重复记忆
版本: 1.0
"""

import re
from collections import Counter
import math
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class Deduplicator:
    """
    自动去重机制通过计算文本相似度，检测并处理重复或高度相似的记忆内容。
    """
    
    def __init__(self, similarity_threshold: float = 0.85, method: str = "cosine") -> None:
        """
        初始化去重器
        
        Args:
            similarity_threshold: 相似度阈值 (0-1)，默认 0.85（85%以上相似视为重复）
            method: 相似度计算方法，支持 "cosine"（默认）、"jaccard"、"levenshtein"
        """
        self.similarity_threshold = similarity_threshold
        self.method = method
        
        if method not in ["cosine", "jaccard", "levenshtein"]:
            logger.warning(f"未知方法 '{method}'，使用默认 'cosine'")
            self.method = "cosine"
    
    def _preprocess_text(self, text: str) -> List[str]:
        """文本预处理：分词、小写、去停用词"""
        # 简单中文分词：按标点和空格分割
        text = text.lower().strip()
        # 移除标点
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        # 分词
        words = [w for w in text.split() if w and len(w) > 1]
        return words
    
    def _get_tfidf_vector(self, text: str, vocab: Dict[str, int]) -> List[float]:
        """计算 TF-IDF 向量（简化版：仅用 TF）"""
        words = self._preprocess_text(text)
        word_count = Counter(words)
        vector = [0.0] * len(vocab)
        
        for word, count in word_count.items():
            if word in vocab:
                # 简单 TF（词频）
                vector[vocab[word]] = count
        
        # 归一化
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        
        return vector
    
    def _cosine_similarity(self, text1: str, text2: str) -> float:
        """计算余弦相似度"""
        # 构建词汇表
        words1 = self._preprocess_text(text1)
        words2 = self._preprocess_text(text2)
        
        if not words1 or not words2:
            return 0.0
        
        # 词汇表
        all_words = list(set(words1 + words2))
        vocab = {word: i for i, word in enumerate(all_words)}
        
        # 计算向量
        vec1 = self._get_tfidf_vector(text1, vocab)
        vec2 = self._get_tfidf_vector(text2, vocab)
        
        # 点积
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        return min(1.0, max(0.0, dot_product))
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """计算 Jaccard 相似度"""
        set1 = set(self._preprocess_text(text1))
        set2 = set(self._preprocess_text(text2))
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _levenshtein_distance(self, text1: str, text2: str) -> float:
        """计算编辑距离相似度"""
        # 简化版：字符级编辑距离
        m, n = len(text1), len(text2)
        if m == 0 or n == 0:
            return 0.0
        
        # 动态规划计算编辑距离
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if text1[i - 1] == text2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]) + 1
        
        distance = dp[m][n]
        max_len = max(m, n)
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """根据配置方法计算相似度"""
        if self.method == "cosine":
            return self._cosine_similarity(text1, text2)
        elif self.method == "jaccard":
            return self._jaccard_similarity(text1, text2)
        elif self.method == "levenshtein":
            return self._levenshtein_distance(text1, text2)
        else:
            return self._cosine_similarity(text1, text2)
    
    def find_duplicates(self, new_content: str, existing_contents: List[str]) -> List[Dict]:
        """
        检测重复内容，返回相似条目列表
        
        Args:
            new_content: 新内容
            existing_contents: 已有内容列表
            
        Returns:
            相似条目列表，每个元素为 {"content": str, "similarity": float}
        """
        duplicates = []
        
        for i, existing in enumerate(existing_contents):
            similarity = self.calculate_similarity(new_content, existing)
            
            if similarity >= self.similarity_threshold:
                duplicates.append({
                    "index": i,
                    "content": existing,
                    "similarity": similarity
                })
        
        # 按相似度降序排序
        duplicates.sort(key=lambda x: x["similarity"], reverse=True)
        return duplicates
    
    def is_duplicate(self, content: str, existing_contents: List[str]) -> bool:
        """
        快速判断是否为重复内容
        
        Args:
            content: 待检测内容
            existing_contents: 已有内容列表
            
        Returns:
            如果存在相似度超过阈值的条目，返回 True
        """
        for existing in existing_contents:
            similarity = self.calculate_similarity(content, existing)
            if similarity >= self.similarity_threshold:
                return True
        return False
    
    def merge_similar(self, entries: List[Dict]) -> Dict:
        """
        合并相似条目，保留最新/最完整的内容
        
        Args:
            entries: 相似条目列表，每个元素应包含至少 "content" 字段
            
        Returns:
            合并后的内容字典，包含合并策略和最终内容
        """
        if not entries:
            return {}
        
        # 简单策略：取最长的内容（假设更完整）
        entries_sorted = sorted(entries, key=lambda x: len(x.get("content", "")), reverse=True)
        longest_content = entries_sorted[0].get("content", "")
        
        # 也可以组合关键信息（简化版）
        all_contents = [entry.get("content", "") for entry in entries]
        unique_sentences = set()
        
        for content in all_contents:
            # 简单分句（按句号、分号、换行）
            sentences = re.split(r'[。；.!?\n]', content)
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and len(sentence) > 5:
                    unique_sentences.add(sentence)
        
        merged_content = "。".join(sorted(unique_sentences)) + "。"
        
        return {
            "strategy": "merge_longest_and_unique",
            "original_count": len(entries),
            "longest_content": longest_content,
            "merged_content": merged_content,
            "unique_sentences": len(unique_sentences)
        }
    
    def suggest_action(self, content: str, existing_contents: List[str]) -> str:
        """
        建议操作
        
        Args:
            content: 新内容
            existing_contents: 已有内容列表
            
        Returns:
            "save" | "merge" | "skip"
        """
        if not existing_contents:
            return "save"
        
        max_similarity = 0.0
        for existing in existing_contents:
            similarity = self.calculate_similarity(content, existing)
            max_similarity = max(max_similarity, similarity)
        
        if max_similarity >= 0.95:
            return "skip"
        elif max_similarity >= self.similarity_threshold:
            return "merge"
        else:
            return "save"

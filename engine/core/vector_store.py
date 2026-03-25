"""
core/vector_store.py — Vector Store with Multi-Backend Embedding Support
向量存储，支持多后端 Embedding

v1.1 改进（2026-03-25）：
  1. 多后端 Embedding 支持：本地 TF-IDF（默认）/ OpenAI / 阿里通义 / HuggingFace
  2. 配置化：EMBEDDING_BACKEND 环境变量切换后端
  3. hybrid_search：正式接收 keyword_results 参数，融合关键词 + 向量结果
  4. 向量存储与 SQLite 索引解耦：向量存储可独立使用

依赖 (Depends on): pathlib, json, logging, math（内置）
可选依赖:
  - openai            → OpenAI text-embedding-3-small
  - httpx, dashscope → 阿里通义 embedding
  - sentence-transformers → 本地 HuggingFace 模型
"""

from __future__ import annotations

import os
import json
import math
import logging
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Embedding Backend 接口
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingBackend:
    """Embedding 后端基类"""

    def encode(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @property
    def dimension(self) -> int:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__class__.__name__


class TFIDFBackend(EmbeddingBackend):
    """
    本地 TF-IDF 向量化（默认后端）。
    无 API 依赖，完全离线可用，适合 < 1000 条记忆的场景。
    """

    def __init__(self):
        self._vocab: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._dimension = 0

    @property
    def dimension(self) -> int:
        return self._dimension or 500

    @property
    def name(self) -> str:
        return "TF-IDF (local)"

    def encode(self, texts: list[str]) -> list[list[float]]:
        """
        TF-IDF 向量化：
          1. 更新词汇表和 IDF
          2. 构建 TF 向量
          3. L2 归一化
        """
        import re
        # Build corpus-level vocab
        doc_freq: dict[str, int] = {}
        all_terms: list[list[str]] = []

        for text in texts:
            terms = self._tokenize(text)
            all_terms.append(terms)
            for t in set(terms):
                doc_freq[t] = doc_freq.get(t, 0) + 1

        n_docs = len(texts)
        # Update IDF
        for term, df in doc_freq.items():
            self._idf[term] = math.log((n_docs + 1) / (df + 1)) + 1

        # Rebuild vocab (new terms only)
        for term in doc_freq:
            if term not in self._vocab:
                self._vocab[term] = len(self._vocab)

        self._dimension = max(len(self._vocab), self._dimension or 0)

        # Build vectors
        vectors: list[list[float]] = []
        for terms in all_terms:
            tf: dict[str, float] = {}
            for t in terms:
                tf[t] = tf.get(t, 0) + 1
            max_tf = max(tf.values()) if tf else 1

            vec = [0.0] * self._dimension
            for t, count in tf.items():
                if t in self._vocab:
                    idx = self._vocab[t]
                    tf_norm = count / max_tf
                    idf = self._idf.get(t, 1.0)
                    vec[idx] = tf_norm * idf

            # L2 normalize
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [x / norm for x in vec]
            vectors.append(vec)

        return vectors

    def _tokenize(self, text: str) -> list[str]:
        import re
        text = text.lower()
        return [
            t for t in re.split(r"[^\w\u4e00-\u9fff]+", text)
            if t and len(t) > 1
        ]


class OpenAIEmbeddingBackend(EmbeddingBackend):
    """OpenAI text-embedding-3-small 后端"""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None):
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._dim = 1536 if "3-small" in model else 3072

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return f"OpenAI {self._model}"

    def encode(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai 库未安装，请运行: pip install openai")

        client = OpenAI(api_key=self._api_key)
        response = client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]


class TongYiEmbeddingBackend(EmbeddingBackend):
    """阿里通义千问 embedding 后端"""

    def __init__(self, api_key: str | None = None, model: str = "text-embedding-v3"):
        try:
            import httpx
            import dashscope
        except ImportError:
            raise ImportError("请安装依赖: pip install httpx dashscope")

        self._api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self._model = model
        self._dim = 1536

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return f"TongYi {self._model}"

    def encode(self, texts: list[str]) -> list[list[float]]:
        import httpx
        import dashscope

        dashscope.api_key = self._api_key
        embeddings = []
        batch_size = 25
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = dashscope.TextEmbedding.call(
                model=self._model,
                input=batch,
            )
            if response.status_code == 200:
                for item in response.output["embeddings"]:
                    embeddings.append(item["embedding"])
            else:
                logger.warning(f"TongYi embedding failed: {response.message}")
                embeddings.extend([[0.0] * self._dim] * len(batch))
        return embeddings


class HuggingFaceEmbeddingBackend(EmbeddingBackend):
    """HuggingFace sentence-transformers 本地模型"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("请安装: pip install sentence-transformers")

        self._model = SentenceTransformer(model_name)
        self._dim = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return f"HuggingFace ({self._model.name})"

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()


# ─────────────────────────────────────────────────────────────────────────────
# 向量存储
# ─────────────────────────────────────────────────────────────────────────────

class VectorStore:
    """
    向量存储：支持多种 Embedding 后端，提供向量搜索 + 混合搜索。

    v1.1 后端自动选择逻辑:
        EMBEDDING_BACKEND=openai     → OpenAI text-embedding-3-small
        EMBEDDING_BACKEND=tongyi     → 阿里通义千问
        EMBEDDING_BACKEND=huggingface→ HuggingFace sentence-transformers
        EMBEDDING_BACKEND=tfidf      → 本地 TF-IDF（默认）

    Usage:
        vs = VectorStore(persist_dir="./memory-bank")
        vs.embedding_backend = OpenAIEmbeddingBackend()  # 可选
        vs.add("entry-1", "我更喜欢简洁的代码")
        results = vs.search("简洁", top_k=5)
        hybrid = vs.hybrid_search("简洁代码", keyword_results=[...], top_k=5)
    """

    def __init__(self, persist_dir: Path):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # 文件路径
        self.vectors_file = self.persist_dir / "vectors.json"
        self.metadata_file = self.persist_dir / "metadata.json"

        # 内存状态
        self.vectors: dict[str, list[float]] = {}
        self.metadata: dict[str, dict[str, Any]] = {}

        # 词汇表（TF-IDF 后端用）
        self.vocabulary: dict[str, int] = {}
        self.vocab_file = self.persist_dir / "vocabulary.json"

        # v1.1: Embedding 后端（默认 TF-IDF）
        self._embedding_backend: EmbeddingBackend = self._auto_backend()

        # 加载
        self._load_from_disk()

    def _auto_backend(self) -> EmbeddingBackend:
        """根据环境变量自动选择 Embedding 后端"""
        backend = os.environ.get("EMBEDDING_BACKEND", "tfidf").lower()
        if backend == "openai":
            return OpenAIEmbeddingBackend()
        elif backend == "tongyi":
            return TongYiEmbeddingBackend()
        elif backend == "huggingface":
            return HuggingFaceEmbeddingBackend()
        else:
            return TFIDFBackend()

    @property
    def embedding_backend(self) -> EmbeddingBackend:
        return self._embedding_backend

    @embedding_backend.setter
    def embedding_backend(self, backend: EmbeddingBackend) -> None:
        self._embedding_backend = backend

    def _load_from_disk(self) -> None:
        try:
            if self.vectors_file.exists():
                with open(self.vectors_file, "r", encoding="utf-8") as f:
                    self.vectors = json.load(f)

            if self.metadata_file.exists():
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)

            if self.vocab_file.exists():
                with open(self.vocab_file, "r", encoding="utf-8") as f:
                    self.vocabulary = json.load(f)

            logger.info(
                f"VectorStore loaded: {len(self.vectors)} vectors, "
                f"backend: {self._embedding_backend.name}"
            )
        except Exception as e:
            logger.warning(f"Failed to load VectorStore: {e}, starting fresh")

    def _save_to_disk(self) -> None:
        try:
            with open(self.vectors_file, "w", encoding="utf-8") as f:
                json.dump(self.vectors, f, ensure_ascii=False, indent=2)

            with open(self.metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)

            with open(self.vocab_file, "w", encoding="utf-8") as f:
                json.dump(self.vocabulary, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save VectorStore: {e}")

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        if not vec1 or not vec2:
            return 0.0

        # Pad vectors to same length
        max_len = max(len(vec1), len(vec2))
        v1_ext = vec1 + [0.0] * (max_len - len(vec1))
        v2_ext = vec2 + [0.0] * (max_len - len(vec2))

        dot_product = sum(a * b for a, b in zip(v1_ext, v2_ext))
        norm1 = math.sqrt(sum(a * a for a in v1_ext))
        norm2 = math.sqrt(sum(b * b for b in v2_ext))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return max(0.0, min(1.0, similarity))

    def add(self, entry_id: str, content: str, metadata: dict[str, Any] | None = None) -> bool:
        """
        添加向量到存储。
        使用当前配置的 Embedding 后端生成向量。
        """
        try:
            vectors = self._embedding_backend.encode([content])
            self.vectors[entry_id] = vectors[0]

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

    def search(self, query: str, top_k: int = 5, filter: dict | None = None) -> list[dict]:
        """
        向量语义搜索。

        Args:
            query: 查询文本
            top_k: 返回数量
            filter: 过滤条件（暂未实现）

        Returns:
            [{"entry_id": str, "score": float, "content": str, "metadata": dict}, ...]
        """
        try:
            query_vector = self._embedding_backend.encode([query])[0]

            results = []
            for entry_id, vector in self.vectors.items():
                similarity = self._cosine_similarity(query_vector, vector)
                if similarity >= 0.1:  # 过滤噪音
                    meta = self.metadata.get(entry_id, {})
                    results.append({
                        "entry_id": entry_id,
                        "score": round(similarity, 4),
                        "content": meta.get("content", ""),
                        "metadata": meta.get("metadata", {}),
                    })

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return []

    def delete(self, entry_id: str) -> bool:
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

    def update(self, entry_id: str, content: str, metadata: dict | None = None) -> bool:
        """更新向量：删除旧向量 + 添加新向量"""
        self.delete(entry_id)
        return self.add(entry_id, content, metadata)

    def get_count(self) -> int:
        """返回向量数量"""
        return len(self.vectors)

    def hybrid_search(
        self,
        query: str,
        keyword_results: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        混合搜索：融合关键词结果 + 向量语义结果。

        融合策略：
          - 向量命中：直接使用向量相似度分数
          - 关键词命中：score = 0.8 - (index * 0.1)（排名衰减）
          - 两者都命中：平均两个分数，标记 source="both"
          - 最终排序：按融合分数降序

        Args:
            query: 查询文本
            keyword_results: 关键词搜索结果列表，每项须包含 id/content/score
            top_k: 返回数量

        Returns:
            [{"entry_id": str, "score": float, "content": str, "source": str}, ...]
        """
        # 向量搜索结果
        vector_results = self.search(query, top_k=top_k * 2)

        # 构建向量结果字典
        combined: dict[str, dict] = {}

        # 关键词结果（从 keyword_results 取）
        for idx, result in enumerate(keyword_results):
            entry_id = result.get("id") or result.get("entry_id") or f"keyword_{idx}"
            combined[entry_id] = {
                "entry_id": entry_id,
                "score": 0.8 - (idx * 0.1),  # 排名衰减
                "content": result.get("content", ""),
                "metadata": result.get("metadata", {}),
                "source": "keyword"
            }

        # 向量结果：合并或新增
        for result in vector_results:
            entry_id = result["entry_id"]
            if entry_id in combined:
                # 两者都命中：平均分数
                combined[entry_id]["score"] = (combined[entry_id]["score"] + result["score"]) / 2
                combined[entry_id]["source"] = "both"
            else:
                combined[entry_id] = {
                    "entry_id": entry_id,
                    "score": result["score"],
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "source": "vector"
                }

        # 排序输出
        combined_list = list(combined.values())
        combined_list.sort(key=lambda x: x["score"], reverse=True)

        return combined_list[:top_k]

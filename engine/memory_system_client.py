#!/usr/bin/env python3
"""
Memory System Client — 记忆系统客户端
为 Adaptive Skill System 提供统一的记忆系统接口
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)


class MemorySystemClient:
    """
    记忆系统客户端，桥接 Adaptive Skill System 和底层记忆系统
    
    提供统一的接口访问 LTM（长期记忆）和 KB（知识库）
    """
    
    def __init__(self, memory_dir: str):
        """
        初始化记忆系统客户端
        
        Args:
            memory_dir: 记忆系统目录路径（包含 memory-bank/）
        """
        self.memory_dir = Path(memory_dir)
        
        # 检查目录是否存在
        if not self.memory_dir.exists():
            raise FileNotFoundError(f"记忆系统目录不存在: {memory_dir}")
        
        # 导入记忆系统模块
        try:
            # 添加当前目录到路径
            sys.path.insert(0, str(Path(__file__).parent))
            
            from core.ltm import LTMManager
            from core.kb import KBManager
            from core.deduplicator import Deduplicator
            from core.vector_store import VectorStore
            from core.weight import MemoryWeight
            
            self.LTMManager = LTMManager
            self.KBManager = KBManager
            self.Deduplicator = Deduplicator
            self.VectorStore = VectorStore
            self.MemoryWeight = MemoryWeight
            
            # 初始化记忆管理器
            memory_bank_path = self.memory_dir / "memory-bank"
            if not memory_bank_path.exists():
                memory_bank_path = self.memory_dir
            
            self.ltm = LTMManager(memory_bank_path)
            self.kb = KBManager(memory_bank_path)
            
            # 初始化其他模块
            self.deduplicator = Deduplicator()
            self.vector_store = VectorStore(memory_bank_path / "vector_store")
            self.weight = MemoryWeight(memory_bank_path)
            
            logger.info(f"记忆系统客户端初始化成功，目录: {memory_dir}")
            
        except ImportError as e:
            logger.error(f"无法导入记忆系统模块: {e}")
            raise RuntimeError(f"记忆系统模块未安装或路径错误: {e}")
        except Exception as e:
            logger.error(f"记忆系统客户端初始化失败: {e}")
            raise RuntimeError(f"记忆系统初始化失败: {e}")
    
    # ========== LTM 代理方法 ==========
    
    def save_memory(self, content: str, category: str = "general", 
                    tags: Optional[List[str]] = None, metadata: Optional[Dict] = None) -> Dict:
        """保存长期记忆"""
        return self.ltm.save(content=content, category=category, tags=tags, metadata=metadata)
    
    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """获取单个记忆"""
        return self.ltm.get(memory_id)
    
    def search_memories(self, query: str, limit: int = 10, 
                        category: Optional[str] = None) -> List[Dict]:
        """搜索长期记忆"""
        return self.ltm.search(query=query, limit=limit, category=category)
    
    def update_memory(self, memory_id: str, content: Optional[str] = None,
                      category: Optional[str] = None, tags: Optional[List[str]] = None) -> bool:
        """更新记忆"""
        return self.ltm.update(memory_id, content=content, category=category, tags=tags)
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        return self.ltm.delete(memory_id)
    
    def list_memories(self, category: Optional[str] = None, 
                      limit: int = 100) -> List[Dict]:
        """列出所有记忆"""
        return self.ltm.list_all(category=category, limit=limit)
    
    def get_user_profile(self) -> Dict:
        """获取用户档案"""
        return self.ltm.load_profile()
    
    # ========== KB 代理方法 ==========
    
    def add_knowledge(self, title: str, content: str, category: str = "general",
                      tags: Optional[List[str]] = None, source: str = "user",
                      confidence: float = 1.0) -> Dict:
        """添加知识库条目"""
        return self.kb.add(title=title, content=content, category=category,
                          tags=tags, source=source, confidence=confidence)
    
    def search_knowledge(self, query: str, limit: int = 10,
                         category: Optional[str] = None) -> List[Dict]:
        """搜索知识库"""
        return self.kb.search(query=query, limit=limit, category=category)
    
    def get_knowledge(self, kb_id: str) -> Optional[Dict]:
        """获取知识库条目"""
        return self.kb.get(kb_id)
    
    def update_knowledge(self, kb_id: str, title: Optional[str] = None,
                         content: Optional[str] = None, tags: Optional[List[str]] = None) -> bool:
        """更新知识库条目"""
        return self.kb.update(kb_id, title=title, content=content, tags=tags)
    
    def delete_knowledge(self, kb_id: str) -> bool:
        """删除知识库条目"""
        return self.kb.delete(kb_id)
    
    def list_knowledge(self, category: Optional[str] = None,
                       limit: int = 100) -> List[Dict]:
        """列出知识库条目"""
        return self.kb.list_all(category=category, limit=limit)
    
    def import_knowledge_text(self, text: str, chunk_size: int = 1000) -> List[Dict]:
        """批量导入文本到知识库"""
        return self.kb.import_text(text, chunk_size=chunk_size)
    
    # ========== 混合搜索方法 ==========
    
    def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        混合搜索：同时搜索 LTM 和 KB，并按相关性合并结果
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            合并后的结果列表
        """
        # 搜索 LTM
        ltm_results = self.search_memories(query, limit=top_k * 2)
        
        # 搜索 KB
        kb_results = self.search_knowledge(query, limit=top_k * 2)
        
        # 向量搜索（如果可用）
        vector_results = []
        try:
            vector_results = self.vector_store.search(query, top_k=top_k * 2)
        except Exception as e:
            logger.debug(f"向量搜索不可用，回退到关键词搜索: {e}")
        
        # 合并结果
        combined = []
        
        # 为 LTM 结果添加分数
        for idx, result in enumerate(ltm_results):
            entry_id = result.get("id", f"ltm_{idx}")
            score = 0.9 - (idx * 0.05)  # 递减分数
            
            combined.append({
                "entry_id": entry_id,
                "source": "ltm",
                "score": score,
                "content": result.get("content", ""),
                "title": f"记忆: {result.get('category', 'general')}",
                "metadata": result,
                "type": "memory"
            })
        
        # 为 KB 结果添加分数
        for idx, result in enumerate(kb_results):
            entry_id = result.get("id", f"kb_{idx}")
            score = 0.8 - (idx * 0.05)  # 递减分数
            
            combined.append({
                "entry_id": entry_id,
                "source": "kb",
                "score": score,
                "content": result.get("content", ""),
                "title": result.get("title", "未知"),
                "metadata": result,
                "type": "knowledge"
            })
        
        # 添加向量结果
        for result in vector_results:
            entry_id = result.get("entry_id", "")
            if any(item["entry_id"] == entry_id for item in combined):
                # 如果已存在，更新分数
                for item in combined:
                    if item["entry_id"] == entry_id:
                        item["score"] = (item["score"] + result["score"]) / 2
                        item["source"] = f"{item['source']}+vector"
            else:
                combined.append({
                    "entry_id": entry_id,
                    "source": "vector",
                    "score": result.get("score", 0.7),
                    "content": result.get("content", ""),
                    "title": f"向量检索: {result.get('metadata', {}).get('category', 'general')}",
                    "metadata": result,
                    "type": "vector"
                })
        
        # 按分数降序排序并限制数量
        combined.sort(key=lambda x: x["score"], reverse=True)
        return combined[:top_k]
    
    # ========== 工具方法 ==========
    
    def is_duplicate(self, content: str, existing_contents: List[str]) -> bool:
        """检查内容是否重复"""
        return self.deduplicator.is_duplicate(content, existing_contents)
    
    def suggest_memory_action(self, content: str, existing_contents: List[str]) -> str:
        """建议记忆操作（save/merge/skip）"""
        return self.deduplicator.suggest_action(content, existing_contents)
    
    def set_memory_weight(self, entry_id: str, weight: int) -> bool:
        """设置记忆权重"""
        return self.weight.set_weight(entry_id, weight)
    
    def rank_results_by_weight(self, results: List[Dict], boost_recent: bool = True) -> List[Dict]:
        """按权重排序结果"""
        return self.weight.rank_results(results, boost_recent)
    
    def auto_suggest_weight(self, content: str, category: str) -> int:
        """自动建议权重"""
        return self.weight.auto_suggest_weight(content, category)
    
    # ========== 系统状态 ==========
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            ltm_count = len(self.ltm.list_all(limit=1000))
            kb_count = len(self.kb.list_all(limit=1000))
            vector_count = self.vector_store.get_count()
            
            return {
                "status": "active",
                "memory_dir": str(self.memory_dir),
                "statistics": {
                    "ltm_entries": ltm_count,
                    "kb_entries": kb_count,
                    "vector_entries": vector_count
                },
                "modules": {
                    "ltm": "available",
                    "kb": "available",
                    "deduplicator": "available",
                    "vector_store": "available",
                    "memory_weight": "available"
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "memory_dir": str(self.memory_dir)
            }
    
    def search_skills_in_kb(self, query: str = "skill", limit: int = 20) -> List[Dict]:
        """
        搜索知识库中的 Skill 条目
        
        Args:
            query: 搜索关键词
            limit: 返回数量
            
        Returns:
            Skill 条目列表
        """
        # 搜索包含 "skill" 标签的条目
        all_kb = self.kb.list_all(limit=1000)
        skills = []
        
        for entry in all_kb:
            tags = entry.get("tags", [])
            title = entry.get("title", "").lower()
            content = entry.get("content", "").lower()
            
            # 检查是否包含 Skill 相关标签
            if any(tag.lower() in ["skill", "流程", "步骤", "方法"] for tag in tags):
                skills.append(entry)
            elif "skill" in title or "技能" in title or "流程" in title:
                skills.append(entry)
            elif "skill" in content or "步骤" in content or "方法" in content:
                # 给较低的优先级
                entry["skill_confidence"] = 0.5
                skills.append(entry)
        
        # 按相关性排序
        if query:
            query_lower = query.lower()
            for entry in skills:
                score = 0.0
                title = entry.get("title", "").lower()
                content = entry.get("content", "").lower()
                
                if query_lower in title:
                    score += 2.0
                if query_lower in content:
                    score += 1.0
                
                entry["relevance_score"] = score
        
        # 按分数排序
        skills.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return skills[:limit]
    
    def search_memories_for_skill_generation(self, problem: str, limit: int = 10) -> List[Dict]:
        """
        为 Skill 生成搜索相关记忆
        
        Args:
            problem: 问题描述
            limit: 返回数量
            
        Returns:
            相关记忆列表
        """
        # 从 LTM 中搜索
        ltm_results = self.search_memories(problem, limit=limit)
        
        # 从 KB 中搜索技能相关条目
        kb_results = self.search_skills_in_kb(problem, limit=limit)
        
        # 合并结果
        combined = []
        
        for result in ltm_results:
            combined.append({
                "source": "ltm",
                "type": "memory",
                "content": result.get("content", ""),
                "metadata": result,
                "relevance": "high"
            })
        
        for result in kb_results:
            combined.append({
                "source": "kb",
                "type": "knowledge",
                "content": result.get("content", ""),
                "metadata": result,
                "relevance": result.get("relevance_score", 0.5) / 2.0
            })
        
        return combined[:limit]


# 简单测试
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 测试路径
    test_paths = [
        Path.cwd() / "memory-bank",
        Path(__file__).parent.parent / "memory-bank",
        Path(__file__).parent / "memory-bank"
    ]
    
    memory_dir = None
    for path in test_paths:
        if path.exists():
            memory_dir = str(path)
            print(f"找到记忆目录: {memory_dir}")
            break
    
    if memory_dir:
        try:
            client = MemorySystemClient(memory_dir)
            status = client.get_system_status()
            print(f"系统状态: {status}")
            
            # 测试搜索
            results = client.search_memories("测试", limit=3)
            print(f"搜索到 {len(results)} 条记忆")
            
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print("未找到记忆目录，请指定 memory_dir 参数")
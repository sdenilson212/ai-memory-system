"""
Memory Weight — 记忆权重系统
支持对记忆的重要性评分，影响检索排序
版本: 1.0
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryWeight:
    """
    记忆权重系统允许用户为每条记忆设置重要性评分，检索时自动按权重排序，确保重要记忆优先呈现。
    """
    
    # 权重常量
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    CORE = 5
    
    # 权重名称映射
    WEIGHT_NAMES = {
        LOW: "低",
        MEDIUM: "中",
        HIGH: "高",
        CRITICAL: "关键",
        CORE: "核心"
    }
    
    def __init__(self, memory_dir: Optional[Path] = None) -> None:
        """
        初始化权重系统
        
        Args:
            memory_dir: 记忆存储目录，如果为 None 则使用内存存储
        """
        self.memory_dir = memory_dir
        self.weight_file: Optional[Path] = None
        
        # 内存存储权重数据 {entry_id: weight}
        self.weights: Dict[str, int] = {}
        
        if memory_dir:
            self.weight_file = memory_dir / "weights.json"
            self._load_weights()
    
    def _load_weights(self) -> None:
        """从文件加载权重数据"""
        if not self.weight_file or not self.weight_file.exists():
            return
        
        try:
            with open(self.weight_file, 'r', encoding='utf-8') as f:
                self.weights = json.load(f)
            logger.info(f"Loaded {len(self.weights)} weight entries")
        except Exception as e:
            logger.warning(f"Failed to load weights: {e}")
    
    def _save_weights(self) -> None:
        """保存权重数据到文件"""
        if not self.weight_file:
            return
        
        try:
            with open(self.weight_file, 'w', encoding='utf-8') as f:
                json.dump(self.weights, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save weights: {e}")
    
    def set_weight(self, entry_id: str, weight: int) -> bool:
        """
        设置记忆权重 (1-5)
        
        Args:
            entry_id: 记忆条目ID
            weight: 权重值 (1-5)
            
        Returns:
            是否成功
        """
        if weight < 1 or weight > 5:
            logger.warning(f"Invalid weight {weight} for entry {entry_id}, must be 1-5")
            return False
        
        self.weights[entry_id] = weight
        self._save_weights()
        logger.debug(f"Set weight {weight} for entry {entry_id}")
        return True
    
    def get_weight(self, entry_id: str) -> int:
        """
        获取记忆权重，默认返回 2 (MEDIUM)
        
        Args:
            entry_id: 记忆条目ID
            
        Returns:
            权重值 (1-5)
        """
        return self.weights.get(entry_id, self.MEDIUM)
    
    def get_weight_name(self, entry_id: str) -> str:
        """
        获取权重名称
        
        Args:
            entry_id: 记忆条目ID
            
        Returns:
            权重名称
        """
        weight = self.get_weight(entry_id)
        return self.WEIGHT_NAMES.get(weight, "未知")
    
    def adjust_weight(self, entry_id: str, delta: int) -> int:
        """
        调整权重值 (+1/-1)
        
        Args:
            entry_id: 记忆条目ID
            delta: 调整值（正数增加，负数减少）
            
        Returns:
            调整后的权重值
        """
        current = self.get_weight(entry_id)
        new_weight = max(self.LOW, min(self.CORE, current + delta))
        
        self.set_weight(entry_id, new_weight)
        logger.debug(f"Adjusted weight for {entry_id}: {current} -> {new_weight} (delta={delta})")
        return new_weight
    
    def rank_results(self, results: List[Dict], boost_recent: bool = True) -> List[Dict]:
        """
        对检索结果按权重排序，可选提升近期记忆
        
        Args:
            results: 搜索结果列表，每个元素应包含至少 "id" 字段
            boost_recent: 是否提升近期记忆
            
        Returns:
            排序后的结果列表
        """
        if not results:
            return []
        
        # 为每个结果计算排序分数
        ranked = []
        for result in results:
            entry_id = result.get("id") or result.get("entry_id", "")
            
            # 基础权重分 (1-5)
            weight = self.get_weight(entry_id)
            weight_score = weight / self.CORE  # 归一化到 0-1
            
            # 时间分（如果有创建时间）
            time_score = 0.0
            if boost_recent:
                created_str = result.get("created_at") or result.get("created", "")
                if created_str:
                    try:
                        # 尝试解析时间
                        created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                        now = datetime.now()
                        
                        # 计算距离现在的天数
                        days_diff = (now - created_dt).days
                        
                        # 时间衰减：7天内满分，30天内半价，超过30天接近0
                        if days_diff <= 7:
                            time_score = 1.0
                        elif days_diff <= 30:
                            time_score = 0.5 * (1 - (days_diff - 7) / 23)
                        else:
                            time_score = 0.1
                    except Exception as e:
                        logger.debug(f"计算时间衰减分失败: {e}")
                else:
                    # 没有时间信息，默认给中等分
                    time_score = 0.3
            
            # 计算总分（权重70%，时间30%）
            total_score = weight_score * 0.7 + time_score * 0.3
            
            # 添加排序信息
            ranked_result = result.copy()
            ranked_result["weight"] = weight
            ranked_result["weight_name"] = self.get_weight_name(entry_id)
            ranked_result["rank_score"] = total_score
            ranked_result["weight_score"] = weight_score
            ranked_result["time_score"] = time_score
            
            ranked.append(ranked_result)
        
        # 按总分降序排序
        ranked.sort(key=lambda x: x["rank_score"], reverse=True)
        return ranked
    
    def auto_suggest_weight(self, content: str, category: str) -> int:
        """
        自动建议权重
        
        Args:
            content: 内容文本
            category: 分类
            
        Returns:
            建议的权重值
        """
        # 凭证类 → 关键
        if category == "credential" or "密码" in content or "密钥" in content:
            return self.CRITICAL
        
        # 偏好/决策 → 高
        if category in ["preference", "decision"]:
            return self.HIGH
        
        # 目标/身份信息 → 高或关键
        if category == "goal" or "我的名字是" in content or "我叫" in content:
            return self.HIGH
        
        # 项目信息 → 中
        if category == "project":
            return self.MEDIUM
        
        # 技术文档/知识 → 中
        if category == "technical":
            return self.MEDIUM
        
        # 闲聊/一般信息 → 低
        if category in ["chat", "general"]:
            return self.LOW
        
        # 默认
        return self.MEDIUM
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取权重统计信息
        
        Returns:
            统计信息字典
        """
        if not self.weights:
            return {}
        
        # 按权重值统计
        weight_counts = {str(weight): 0 for weight in range(1, 6)}
        for weight in self.weights.values():
            weight_counts[str(weight)] = weight_counts.get(str(weight), 0) + 1
        
        # 计算平均权重
        total = sum(self.weights.values())
        count = len(self.weights)
        avg_weight = total / count if count > 0 else 0
        
        return {
            "total_entries": count,
            "average_weight": round(avg_weight, 2),
            "weight_distribution": weight_counts,
            "weight_names": self.WEIGHT_NAMES
        }
    
    def bulk_set_weights(self, weight_map: Dict[str, int]) -> bool:
        """
        批量设置权重
        
        Args:
            weight_map: {entry_id: weight} 映射
            
        Returns:
            是否成功
        """
        success = True
        for entry_id, weight in weight_map.items():
            if weight < 1 or weight > 5:
                logger.warning(f"Invalid weight {weight} for entry {entry_id}")
                success = False
                continue
            
            self.weights[entry_id] = weight
        
        if success:
            self._save_weights()
        
        return success
    
    def clear_weights(self) -> None:
        """清除所有权重"""
        self.weights.clear()
        if self.weight_file and self.weight_file.exists():
            try:
                self.weight_file.unlink()
            except Exception as e:
                logger.warning(f"删除权重文件失败: {e}")
        logger.info("Cleared all weight entries")

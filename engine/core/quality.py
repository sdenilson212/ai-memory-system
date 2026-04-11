"""
core/quality.py — Memory Quality Evaluator
记忆质量评估器

职责 (Responsibility):
    - 评估记忆条目的质量维度
    - 提供质量评分和改进建议
    - 支持质量趋势分析

质量维度:
    - Accuracy (准确性): 内容是否正确/有用
    - Freshness (时效性): 信息是否过时
    - Relevance (相关性): 与用户需求的相关程度
    - Completeness (完整性): 信息是否完整

暴露接口 (Exposes):
    QualityEvaluator.evaluate(entry) -> QualityReport
    QualityEvaluator.evaluate_batch(entries) -> list[QualityReport]
    QualityEvaluator.get_improvement_suggestions(report) -> list[str]
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.ltm import LTMEntry


class QualityDimension(str, Enum):
    """质量评估维度"""
    ACCURACY = "accuracy"         # 准确性
    FRESHNESS = "freshness"       # 时效性
    RELEVANCE = "relevance"       # 相关性
    COMPLETENESS = "completeness" # 完整性


@dataclass
class QualityScores:
    """各维度质量分数（0.0-1.0）"""
    accuracy: float = 0.0
    freshness: float = 0.0
    relevance: float = 0.0
    completeness: float = 0.0
    
    @property
    def overall(self) -> float:
        """综合质量分（加权平均）"""
        weights = {"accuracy": 0.3, "freshness": 0.2, "relevance": 0.3, "completeness": 0.2}
        return (
            self.accuracy * weights["accuracy"] +
            self.freshness * weights["freshness"] +
            self.relevance * weights["relevance"] +
            self.completeness * weights["completeness"]
        )


@dataclass
class QualityReport:
    """质量评估报告"""
    entry_id: str
    scores: QualityScores
    grade: str  # A/B/C/D/F
    suggestions: list[str] = field(default_factory=list)
    evaluated_at: str = ""
    
    @classmethod
    def from_scores(cls, entry_id: str, scores: QualityScores) -> QualityReport:
        """从分数生成报告"""
        overall = scores.overall
        if overall >= 0.9:
            grade = "A"
        elif overall >= 0.8:
            grade = "B"
        elif overall >= 0.7:
            grade = "C"
        elif overall >= 0.6:
            grade = "D"
        else:
            grade = "F"
        
        return cls(
            entry_id=entry_id,
            scores=scores,
            grade=grade,
            evaluated_at=datetime.now().isoformat()
        )


class QualityEvaluator:
    """
    记忆质量评估器。
    
    Usage:
        evaluator = QualityEvaluator()
        
        # 评估单条记忆
        report = evaluator.evaluate(entry, query_context="用户偏好")
        print(f"Quality: {report.grade} ({report.scores.overall:.2f})")
        
        # 获取改进建议
        suggestions = evaluator.get_improvement_suggestions(report)
        for s in suggestions:
            print(f"- {s}")
    """

    # 内容长度评分阈值
    _LENGTH_THRESHOLDS = {
        "minimal": (0, 20),      # 太短
        "short": (20, 100),      # 简短
        "optimal": (100, 1000),  # 最佳
        "long": (1000, 5000),    # 较长
        "excessive": (5000, float('inf')),  # 过长
    }

    def __init__(self, memory_dir: Path | None = None) -> None:
        """
        Args:
            memory_dir: 可选，用于获取额外上下文
        """
        self._memory_dir = memory_dir

    def evaluate(self, entry: LTMEntry, query_context: str = "") -> QualityReport:
        """
        评估单条记忆的质量。
        
        Args:
            entry: 记忆条目
            query_context: 可选的查询上下文（用于相关性评估）
        
        Returns:
            质量评估报告
        """
        scores = QualityScores()
        
        # 1. 准确性评估（基于内容质量指标）
        scores.accuracy = self._evaluate_accuracy(entry)
        
        # 2. 时效性评估（基于创建时间）
        scores.freshness = self._evaluate_freshness(entry)
        
        # 3. 相关性评估（基于内容与上下文匹配）
        scores.relevance = self._evaluate_relevance(entry, query_context)
        
        # 4. 完整性评估（基于内容结构）
        scores.completeness = self._evaluate_completeness(entry)
        
        # 生成报告
        report = QualityReport.from_scores(entry.id, scores)
        report.suggestions = self._generate_suggestions(entry, scores)
        
        return report

    def evaluate_batch(
        self,
        entries: list[LTMEntry],
        query_context: str = ""
    ) -> list[QualityReport]:
        """
        批量评估多条记忆。
        
        Args:
            entries: 记忆条目列表
            query_context: 可选的查询上下文
        
        Returns:
            质量评估报告列表
        """
        return [self.evaluate(e, query_context) for e in entries]

    def get_quality_distribution(self, reports: list[QualityReport]) -> dict:
        """
        获取质量分布统计。
        
        Returns:
            {"A": count, "B": count, ...}
        """
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for report in reports:
            distribution[report.grade] = distribution.get(report.grade, 0) + 1
        return distribution

    def get_low_quality_entries(self, reports: list[QualityReport], threshold: float = 0.6) -> list[str]:
        """
        获取低质量条目 ID。
        
        Args:
            reports: 质量报告列表
            threshold: 质量分阈值
        
        Returns:
            低质量条目 ID 列表
        """
        return [r.entry_id for r in reports if r.scores.overall < threshold]

    def get_improvement_suggestions(self, report: QualityReport) -> list[str]:
        """
        获取改进建议。
        
        Args:
            report: 质量报告
        
        Returns:
            建议列表
        """
        return report.suggestions

    # ── Private Evaluation Methods ────────────────────────────────────────────

    def _evaluate_accuracy(self, entry: LTMEntry) -> float:
        """
        评估准确性。
        
        启发式指标：
        - 是否包含具体信息 vs 模糊表述
        - 是否有来源标注
        - 是否包含可验证的事实
        """
        content = entry.content
        score = 0.7  # 基础分
        
        # 具体性指标：包含数字、日期、具体名称
        if any(c.isdigit() for c in content):
            score += 0.1
        
        # 来源标注（如"根据..."、"来源："）
        source_indicators = ["根据", "来源", "参考", "source", "from", "based on"]
        if any(ind in content.lower() for ind in source_indicators):
            score += 0.1
        
        # 结构化内容（列表、步骤等）
        if any(marker in content for marker in ["1.", "2.", "- ", "* "]):
            score += 0.05
        
        # 惩罚模糊表述
        vague_terms = ["可能", "大概", "应该", "也许", "probably", "maybe", "should"]
        vague_count = sum(1 for term in vague_terms if term in content.lower())
        score -= min(vague_count * 0.05, 0.2)
        
        return max(0.0, min(1.0, score))

    def _evaluate_freshness(self, entry: LTMEntry) -> float:
        """
        评估时效性。
        
        基于创建时间的衰减函数。
        """
        if not entry.created_at:
            return 0.5  # 未知时间给中等分
        
        try:
            # 解析时间
            created = datetime.fromisoformat(entry.created_at.replace("Z", "+00:00"))
            age_days = (datetime.now() - created).days
            
            # 衰减函数：30天内 1.0，之后指数衰减
            if age_days < 30:
                return 1.0
            elif age_days < 90:
                return 0.9
            elif age_days < 180:
                return 0.75
            elif age_days < 365:
                return 0.6
            else:
                # 超过1年：继续衰减但保持最低0.2
                return max(0.2, 0.5 ** (age_days / 365))
        except Exception:
            return 0.5

    def _evaluate_relevance(self, entry: LTMEntry, query_context: str) -> float:
        """
        评估相关性。
        
        基于内容与查询上下文的匹配程度。
        """
        if not query_context:
            return 0.7  # 无上下文给中等分
        
        content = entry.content.lower()
        query = query_context.lower()
        
        # 关键词匹配
        query_words = set(query.split())
        if not query_words:
            return 0.7
        
        matched = sum(1 for word in query_words if word in content)
        match_ratio = matched / len(query_words)
        
        # 类别匹配
        category_bonus = 0.1 if entry.category in query else 0
        
        # 标签匹配
        tag_bonus = 0
        for tag in entry.tags:
            if tag.lower() in query:
                tag_bonus += 0.05
        tag_bonus = min(tag_bonus, 0.2)
        
        score = match_ratio * 0.8 + category_bonus + tag_bonus
        return min(1.0, score)

    def _evaluate_completeness(self, entry: LTMEntry) -> float:
        """
        评估完整性。
        
        基于内容结构和长度。
        """
        content = entry.content
        length = len(content)
        
        # 长度评分
        if length < 20:
            length_score = 0.3  # 太短
        elif length < 100:
            length_score = 0.6
        elif length < 1000:
            length_score = 0.9  # 最佳长度
        elif length < 5000:
            length_score = 0.8
        else:
            length_score = 0.6  # 过长可能冗余
        
        # 结构完整性
        structure_score = 0.7
        
        # 是否有上下文背景
        if any(w in content.lower() for w in ["原因", "理由", "因为", "原因", "because", "reason", "why"]):
            structure_score += 0.1
        
        # 是否有结论/总结
        if any(w in content.lower() for w in ["结论", "总结", "因此", "conclusion", "summary"]):
            structure_score += 0.1
        
        # 标签完整性（有标签加分）
        tag_score = min(len(entry.tags) * 0.05, 0.1)
        
        return min(1.0, length_score * 0.6 + structure_score * 0.3 + tag_score)

    def _generate_suggestions(self, entry: LTMEntry, scores: QualityScores) -> list[str]:
        """生成改进建议"""
        suggestions = []
        
        if scores.accuracy < 0.7:
            suggestions.append("添加更多具体信息或数据来源以提高准确性")
        
        if scores.freshness < 0.6:
            suggestions.append("此记忆可能已过时，建议更新或归档")
        
        if scores.completeness < 0.7:
            if len(entry.content) < 50:
                suggestions.append("内容过短，建议补充更多细节")
            else:
                suggestions.append("建议添加背景说明或结论以提高完整性")
        
        if len(entry.tags) < 2:
            suggestions.append("建议添加更多标签以便检索")
        
        return suggestions

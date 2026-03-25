"""
Skill 质量评估引擎
用于评估自动生成或组合的 Skill 是否可信任和可靠
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QualityAssessment:
    """质量评估结果"""
    skill_id: str
    overall_score: float  # 0-1
    dimensions: Dict[str, float]  # 各个维度的分数
    recommendations: List[str]  # 改进建议
    is_approved: bool  # 是否通过审核
    confidence_level: str  # "high", "medium", "low"
    assessment_time: datetime = None
    
    def to_dict(self) -> Dict:
        return {
            "skill_id": self.skill_id,
            "overall_score": self.overall_score,
            "dimensions": self.dimensions,
            "recommendations": self.recommendations,
            "is_approved": self.is_approved,
            "confidence_level": self.confidence_level,
            "assessment_time": self.assessment_time.isoformat() if self.assessment_time else None
        }


class QualityEvaluator:
    """
    质量评估引擎
    用于评估 Skill 的质量和可靠性
    """
    
    def __init__(self):
        # 质量评估的不同维度及权重
        self.assessment_dimensions = {
            "completeness": 0.20,  # 完整性：步骤是否完整，是否遗漏关键要素
            "clarity": 0.15,  # 清晰度：步骤描述是否清晰易懂
            "feasibility": 0.20,  # 可行性：是否能实际执行
            "evidence_support": 0.20,  # 证据支持：有没有充分的理由或参考
            "generalizability": 0.10,  # 泛化性：是否适用于更广泛的场景
            "novelty": 0.05,  # 新颖性：是否提供了新的视角
            "risk_mitigation": 0.10  # 风险缓解：是否识别并缓解了潜在风险
        }
    
    def assess_skill_quality(self, skill_data: Dict) -> QualityAssessment:
        """
        评估 Skill 的质量
        
        Args:
            skill_data: Skill 数据
        
        Returns:
            QualityAssessment
        """
        skill_id = skill_data.get("skill_id", "unknown")
        
        # 评估各维度
        dimension_scores = {}
        
        dimension_scores["completeness"] = self._assess_completeness(skill_data)
        dimension_scores["clarity"] = self._assess_clarity(skill_data)
        dimension_scores["feasibility"] = self._assess_feasibility(skill_data)
        dimension_scores["evidence_support"] = self._assess_evidence_support(skill_data)
        dimension_scores["generalizability"] = self._assess_generalizability(skill_data)
        dimension_scores["novelty"] = self._assess_novelty(skill_data)
        dimension_scores["risk_mitigation"] = self._assess_risk_mitigation(skill_data)
        
        # 计算总体分数
        overall_score = sum(
            dimension_scores[dim] * weight 
            for dim, weight in self.assessment_dimensions.items()
        )
        
        # 确定是否通过
        is_approved = overall_score >= 0.70
        
        # 生成建议
        recommendations = self._generate_recommendations(dimension_scores, skill_data)
        
        # 确定置信度
        confidence_level = self._determine_confidence_level(skill_data, overall_score)
        
        assessment = QualityAssessment(
            skill_id=skill_id,
            overall_score=overall_score,
            dimensions=dimension_scores,
            recommendations=recommendations,
            is_approved=is_approved,
            confidence_level=confidence_level,
            assessment_time=datetime.now()
        )
        
        return assessment
    
    def _assess_completeness(self, skill_data: Dict) -> float:
        """
        评估完整性
        检查步骤是否完整，是否遗漏关键要素
        """
        steps = skill_data.get("steps", [])
        
        if not steps:
            return 0.0
        
        # 基础分：步骤数量（一般 3-7 步较为合理）
        step_count_score = min(len(steps) / 5, 1.0) * 0.3
        
        # 步骤描述完整性
        step_description_score = 0.0
        for step in steps:
            if step.get("description") and len(step.get("description", "")) > 10:
                step_description_score += 1
        step_description_score = (step_description_score / len(steps)) * 0.4
        
        # 检查关键步骤（如果有的话）
        key_steps = ["分析", "验证", "总结", "反馈"]
        key_step_coverage = 0.0
        for key_step in key_steps:
            for step in steps:
                if key_step in step.get("name", "") or key_step in step.get("description", ""):
                    key_step_coverage += 0.25
                    break
        key_step_coverage = min(key_step_coverage, 1.0) * 0.3
        
        return step_count_score + step_description_score + key_step_coverage
    
    def _assess_clarity(self, skill_data: Dict) -> float:
        """
        评估清晰度
        检查描述是否清晰易懂
        """
        steps = skill_data.get("steps", [])
        description = skill_data.get("description", "")
        
        if not steps:
            return 0.0
        
        clarity_score = 0.0
        
        # 描述的清晰度
        if description and len(description) > 20:
            clarity_score += 0.3
        
        # 步骤名称的清晰度
        clear_names = 0
        for step in steps:
            name = step.get("name", "")
            # 检查是否有明确的动词
            has_verb = any(verb in name for verb in ["分析", "评估", "计算", "确定", "验证", "执行"])
            if has_verb or len(name) > 3:
                clear_names += 1
        
        clarity_score += (clear_names / len(steps)) * 0.4
        
        # 步骤间的逻辑连接
        logic_score = self._assess_step_logic(steps)
        clarity_score += logic_score * 0.3
        
        return min(clarity_score, 1.0)
    
    def _assess_feasibility(self, skill_data: Dict) -> float:
        """
        评估可行性
        检查是否能实际执行
        """
        steps = skill_data.get("steps", [])
        generation_info = skill_data.get("generation_info", {})
        
        if not steps:
            return 0.0
        
        feasibility_score = 0.0
        
        # 步骤是否有具体的执行细节
        detailed_steps = 0
        for step in steps:
            description = step.get("description", "")
            if description and len(description) > 30:
                detailed_steps += 1
        
        feasibility_score += (detailed_steps / len(steps)) * 0.4
        
        # 是否标记为自动生成且未验证
        if generation_info.get("type") == "auto-generated" and generation_info.get("needs_verification"):
            feasibility_score += 0.2  # 降低分数
        else:
            feasibility_score += 0.3
        
        # 置信度（如果有的话）
        confidence = generation_info.get("confidence", 0.5)
        feasibility_score += confidence * 0.3
        
        return min(feasibility_score, 1.0)
    
    def _assess_evidence_support(self, skill_data: Dict) -> float:
        """
        评估证据支持
        检查有没有充分的理由或参考
        """
        generation_info = skill_data.get("generation_info", {})
        
        support_score = 0.0
        
        # LTM 参考
        ltm_references = generation_info.get("ltm_references", [])
        if ltm_references:
            support_score += min(len(ltm_references) / 3, 1.0) * 0.4
        
        # 基础 Skill
        base_skills = generation_info.get("base_skills", [])
        if base_skills:
            support_score += min(len(base_skills) / 2, 1.0) * 0.3
        
        # 生成理由
        rationale = skill_data.get("rationale", "")
        if rationale and len(rationale) > 10:
            support_score += 0.3
        
        return min(support_score, 1.0)
    
    def _assess_generalizability(self, skill_data: Dict) -> float:
        """
        评估泛化性
        检查是否适用于更广泛的场景
        """
        steps = skill_data.get("steps", [])
        description = skill_data.get("description", "")
        
        # 是否使用了过度具体的术语
        specific_terms = ["本公司", "我们的", "这个项目", "该产品"]
        specificity = sum(1 for term in specific_terms if term in description)
        
        generalizability_score = max(1.0 - (specificity * 0.2), 0.3)
        
        # 步骤是否过度专业化
        generic_verbs = ["分析", "评估", "设计", "规划", "验证", "改进"]
        generic_step_count = 0
        
        for step in steps:
            name = step.get("name", "")
            if any(verb in name for verb in generic_verbs):
                generic_step_count += 1
        
        if steps:
            generalizability_score += (generic_step_count / len(steps)) * 0.5
        
        return min(generalizability_score, 1.0)
    
    def _assess_novelty(self, skill_data: Dict) -> float:
        """
        评估新颖性
        检查是否提供了新的视角
        """
        generation_info = skill_data.get("generation_info", {})
        skill_type = generation_info.get("type", "manual")
        
        # 自动生成的通常更新颖
        if skill_type == "auto-generated":
            novelty_score = 0.6
        elif skill_type == "composed":
            novelty_score = 0.5
        else:
            novelty_score = 0.3
        
        # 如果有新的组合方式，增加新颖性评分
        base_skills = generation_info.get("base_skills", [])
        if len(base_skills) >= 2:
            novelty_score += 0.3
        
        return min(novelty_score, 1.0)
    
    def _assess_risk_mitigation(self, skill_data: Dict) -> float:
        """
        评估风险缓解
        检查是否识别并缓解了潜在风险
        """
        potential_issues = skill_data.get("potential_issues", [])
        verification_checklist = skill_data.get("verification_checklist", [])
        
        risk_score = 0.0
        
        # 是否有潜在问题识别
        if potential_issues and len(potential_issues) > 0:
            risk_score += 0.3
        
        # 是否有验证清单
        if verification_checklist and len(verification_checklist) > 0:
            risk_score += 0.4
        
        # 是否标记了需要验证
        generation_info = skill_data.get("generation_info", {})
        if generation_info.get("needs_verification"):
            risk_score += 0.3
        
        return min(risk_score, 1.0)
    
    def _assess_step_logic(self, steps: List[Dict]) -> float:
        """评估步骤之间的逻辑连接"""
        if len(steps) < 2:
            return 0.8
        
        # 简单的逻辑检查：后续步骤是否合理
        logical_progressions = [
            ("分析", ["评估", "设计", "计划"]),
            ("规划", ["执行", "实施", "验证"]),
            ("验证", ["总结", "反馈", "改进"])
        ]
        
        logic_score = 0.0
        for i in range(len(steps) - 1):
            current_step = steps[i].get("name", "")
            next_step = steps[i + 1].get("name", "")
            
            # 检查是否有合理的进展
            for from_step, to_steps in logical_progressions:
                if from_step in current_step and any(to_step in next_step for to_step in to_steps):
                    logic_score += 1
                    break
        
        return min(logic_score / (len(steps) - 1), 1.0)
    
    def _generate_recommendations(self, dimension_scores: Dict, skill_data: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 完整性建议
        if dimension_scores["completeness"] < 0.6:
            recommendations.append("增加或细化步骤，确保过程完整")
        
        # 清晰度建议
        if dimension_scores["clarity"] < 0.6:
            recommendations.append("提高步骤描述的清晰度，使用更具体的语言")
        
        # 可行性建议
        if dimension_scores["feasibility"] < 0.6:
            recommendations.append("提供更多执行细节，确保 Skill 可实际操作")
        
        # 证据支持建议
        if dimension_scores["evidence_support"] < 0.5:
            recommendations.append("添加更多 LTM 参考或基础 Skill")
        
        # 新颖性建议
        if dimension_scores["novelty"] < 0.3:
            recommendations.append("尝试新的组合或视角来提高创新性")
        
        # 风险缓解建议
        if dimension_scores["risk_mitigation"] < 0.5:
            recommendations.append("识别并列出潜在风险，创建验证清单")
        
        # 通用建议
        if not recommendations:
            recommendations.append("Skill 质量良好，可以使用")
        
        return recommendations
    
    def _determine_confidence_level(self, skill_data: Dict, overall_score: float) -> str:
        """确定置信度水平"""
        generation_info = skill_data.get("generation_info", {})
        
        if generation_info.get("type") == "manual":
            # 手动创建的 Skill 通常高置信度
            if overall_score >= 0.75:
                return "high"
            else:
                return "medium"
        elif generation_info.get("type") == "composed":
            # 组合的 Skill
            if overall_score >= 0.80:
                return "high"
            elif overall_score >= 0.65:
                return "medium"
            else:
                return "low"
        else:  # auto-generated
            # 自动生成的 Skill
            if overall_score >= 0.85:
                return "high"
            elif overall_score >= 0.70:
                return "medium"
            else:
                return "low"
    
    def create_approval_summary(self, assessment: QualityAssessment, skill_data: Dict) -> Dict:
        """
        创建审批总结
        用于决定是否将 Skill 保存到 KB
        """
        summary = {
            "approved": assessment.is_approved,
            "overall_score": assessment.overall_score,
            "confidence": assessment.confidence_level,
            "dimensions": assessment.dimensions,
            "recommendations": assessment.recommendations,
            "status": "ready_for_use" if assessment.is_approved else "needs_improvement",
            "action": "save_to_kb" if assessment.is_approved else "collect_feedback"
        }
        
        if not assessment.is_approved:
            summary["improvement_needed"] = True
            summary["next_steps"] = [
                "根据建议进行改进",
                "重新提交评估",
                "或收集用户反馈后优化"
            ]
        
        return summary

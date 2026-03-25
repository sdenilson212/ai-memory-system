"""
Skill 组合引擎 - Layer 2 实现
用于从 LTM 中搜索、评估和组合多个知识源来生成新 Skill
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import math
from datetime import datetime


@dataclass
class LTMSearchResult:
    """LTM 搜索结果"""
    memory_id: str
    content: str
    category: str
    tags: List[str]
    relevance_score: float  # 0-1
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "relevance_score": self.relevance_score,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class CompositionPlan:
    """Skill 组合计划"""
    base_framework: str  # 使用哪个基础框架
    components: List[Dict]  # 组成部分：[{"source": "记忆ID", "aspect": "价值主张"}]
    adaptation_strategy: Dict  # 适配策略
    estimated_quality: float  # 预计质量评分 0-1
    
    def to_dict(self) -> Dict:
        return {
            "base_framework": self.base_framework,
            "components": self.components,
            "adaptation_strategy": self.adaptation_strategy,
            "estimated_quality": self.estimated_quality
        }


class SkillComposer:
    """
    Skill 组合引擎
    负责从 LTM 中提取和组合信息来生成新 Skill
    """
    
    def __init__(self, ltm_client=None, kb_client=None):
        self.ltm = ltm_client
        self.kb = kb_client
        self.common_frameworks = {
            "business_planning": {
                "steps": ["市场分析", "竞争分析", "资源评估", "风险评估", "计划制定"],
                "inputs": ["业务目标", "市场信息"],
                "outputs": ["商业计划"]
            },
            "product_optimization": {
                "steps": ["需求分析", "用户研究", "设计迭代", "测试验证", "发布"],
                "inputs": ["产品信息", "用户数据"],
                "outputs": ["优化方案"]
            },
            "marketing_strategy": {
                "steps": ["目标定位", "渠道选择", "内容制定", "预算分配", "效果评估"],
                "inputs": ["产品特征", "目标人群"],
                "outputs": ["营销策略"]
            },
            "problem_solving": {
                "steps": ["问题定义", "原因分析", "方案设计", "方案评估", "执行计划"],
                "inputs": ["问题描述"],
                "outputs": ["解决方案"]
            }
        }
    
    def analyze_problem(self, problem: str) -> Dict:
        """
        分析问题的特征，识别最适合的框架
        
        Args:
            problem: 问题描述
        
        Returns:
            问题分析结果
        """
        analysis = {
            "problem_type": self._classify_problem(problem),
            "keywords": self._extract_keywords(problem),
            "required_expertise": self._identify_expertise(problem),
            "complexity_level": self._assess_complexity(problem)
        }
        return analysis
    
    def search_ltm(self, problem: str, keywords: List[str], max_results: int = 10) -> List[LTMSearchResult]:
        """
        从 LTM 中搜索相关信息
        
        Args:
            problem: 问题
            keywords: 关键词列表
            max_results: 最大返回结果数
        
        Returns:
            搜索结果列表
        """
        if not self.ltm:
            return []
        
        results = []
        for keyword in keywords:
            # 调用 LTM 搜索
            ltm_results = self.ltm.recall(query=keyword)
            
            for ltm_item in ltm_results:
                relevance_score = self._calculate_relevance(ltm_item, problem, keyword)
                
                result = LTMSearchResult(
                    memory_id=ltm_item.get("id", "unknown"),
                    content=ltm_item.get("content", ""),
                    category=ltm_item.get("category", "general"),
                    tags=ltm_item.get("tags", []),
                    relevance_score=relevance_score,
                    timestamp=datetime.now()
                )
                results.append(result)
        
        # 按相关性排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:max_results]
    
    def assess_composability(self, ltm_results: List[LTMSearchResult], problem: str) -> Tuple[bool, Dict]:
        """
        评估是否能从这些 LTM 结果中组合出 Skill
        
        Args:
            ltm_results: LTM 搜索结果
            problem: 原始问题
        
        Returns:
            (能否组合, 评估信息)
        """
        if not ltm_results:
            return False, {"reason": "No relevant information found"}
        
        # 计算覆盖度
        coverage = self._calculate_coverage(ltm_results, problem)
        
        # 计算多样性（确保信息来自不同维度）
        diversity = self._calculate_diversity(ltm_results)
        
        # 计算整体可组合性
        composability_score = 0.6 * coverage + 0.4 * diversity
        
        can_compose = composability_score >= 0.65  # 阈值
        
        return can_compose, {
            "coverage_score": coverage,
            "diversity_score": diversity,
            "composability_score": composability_score,
            "info_count": len(ltm_results),
            "avg_relevance": sum(r.relevance_score for r in ltm_results) / len(ltm_results)
        }
    
    def create_composition_plan(self, problem: str, ltm_results: List[LTMSearchResult], 
                               problem_analysis: Dict) -> CompositionPlan:
        """
        创建组合计划
        
        Args:
            problem: 问题
            ltm_results: LTM 搜索结果
            problem_analysis: 问题分析结果
        
        Returns:
            CompositionPlan
        """
        # 选择最适合的框架
        framework_name = self._select_framework(problem_analysis)
        base_framework = self.common_frameworks.get(framework_name)
        
        if not base_framework:
            framework_name = "problem_solving"
            base_framework = self.common_frameworks[framework_name]
        
        # 识别哪些 LTM 对应哪些步骤
        components = []
        for i, step in enumerate(base_framework["steps"]):
            # 找最相关的 LTM 信息
            relevant_ltm = self._match_ltm_to_step(step, ltm_results)
            if relevant_ltm:
                components.append({
                    "step": step,
                    "source": relevant_ltm.memory_id,
                    "aspect": relevant_ltm.tags[0] if relevant_ltm.tags else "general",
                    "relevance": relevant_ltm.relevance_score
                })
            else:
                components.append({
                    "step": step,
                    "source": "framework",
                    "aspect": "template",
                    "relevance": 0.5  # 使用框架默认值
                })
        
        # 制定适配策略
        adaptation_strategy = self._create_adaptation_strategy(
            framework_name,
            problem_analysis,
            components
        )
        
        # 估计质量
        estimated_quality = self._estimate_composition_quality(components, ltm_results)
        
        return CompositionPlan(
            base_framework=framework_name,
            components=components,
            adaptation_strategy=adaptation_strategy,
            estimated_quality=estimated_quality
        )
    
    # ==================== 私有方法 ====================
    
    def _classify_problem(self, problem: str) -> str:
        """分类问题类型"""
        problem_lower = problem.lower()
        
        if any(word in problem_lower for word in ["商业", "business", "plan", "计划", "策略"]):
            return "business_planning"
        elif any(word in problem_lower for word in ["产品", "product", "优化", "design"]):
            return "product_optimization"
        elif any(word in problem_lower for word in ["营销", "marketing", "推广", "宣传"]):
            return "marketing_strategy"
        else:
            return "problem_solving"
    
    def _extract_keywords(self, problem: str) -> List[str]:
        """从问题中提取关键词"""
        # 简单的关键词提取（实际应用中可用 NLP）
        stop_words = {"怎么", "如何", "为什么", "什么", "呢", "吗", "的", "了", "和", "或", "是"}
        
        # 分割问题
        words = problem.split()
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        
        return keywords[:5]  # 返回前 5 个关键词
    
    def _identify_expertise(self, problem: str) -> List[str]:
        """识别所需的专业领域"""
        problem_lower = problem.lower()
        expertise = []
        
        expertise_map = {
            "psychology": ["心理学", "用户", "行为", "motivation"],
            "data_analysis": ["数据", "分析", "统计", "metrics"],
            "finance": ["预算", "成本", "ROI", "财务"],
            "distribution": ["渠道", "发行", "delivery"],
            "product": ["产品", "特征", "功能"]
        }
        
        for domain, keywords in expertise_map.items():
            if any(keyword in problem_lower for keyword in keywords):
                expertise.append(domain)
        
        return expertise
    
    def _assess_complexity(self, problem: str) -> str:
        """评估问题复杂度"""
        problem_len = len(problem)
        keyword_count = len(self._extract_keywords(problem))
        
        if problem_len < 50:
            return "low"
        elif problem_len < 200 and keyword_count <= 5:
            return "medium"
        else:
            return "high"
    
    def _calculate_relevance(self, ltm_item: Dict, problem: str, keyword: str) -> float:
        """计算 LTM 项与问题的相关性"""
        score = 0.0
        
        # 完全匹配
        if keyword in ltm_item.get("content", ""):
            score += 0.4
        
        # 标签匹配
        tags = ltm_item.get("tags", [])
        if any(keyword in tag for tag in tags):
            score += 0.3
        
        # 分类匹配
        if ltm_item.get("category") in ["discussion", "insight", "method"]:
            score += 0.2
        
        # 新近性（更新的记忆更相关）
        # 这里简化处理，实际可加入时间权重
        score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_coverage(self, ltm_results: List[LTMSearchResult], problem: str) -> float:
        """计算信息覆盖度"""
        if not ltm_results:
            return 0.0
        
        # 计算有多少比例的搜索结果相关性较高
        high_relevance_count = sum(1 for r in ltm_results if r.relevance_score >= 0.6)
        coverage = high_relevance_count / len(ltm_results)
        
        return coverage
    
    def _calculate_diversity(self, ltm_results: List[LTMSearchResult]) -> float:
        """计算信息多样性（来自不同维度）"""
        if not ltm_results:
            return 0.0
        
        # 统计不同的标签和分类
        all_tags = set()
        categories = set()
        
        for result in ltm_results:
            all_tags.update(result.tags)
            categories.add(result.category)
        
        # 多样性 = (不同标签 + 不同分类) / (总记忆数 * 2)
        diversity = (len(all_tags) + len(categories)) / (len(ltm_results) * 2)
        
        return min(diversity, 1.0)
    
    def _select_framework(self, problem_analysis: Dict) -> str:
        """根据问题分析选择最适合的框架"""
        problem_type = problem_analysis.get("problem_type", "problem_solving")
        
        if problem_type in self.common_frameworks:
            return problem_type
        else:
            return "problem_solving"
    
    def _match_ltm_to_step(self, step: str, ltm_results: List[LTMSearchResult]) -> Optional[LTMSearchResult]:
        """将 LTM 信息匹配到步骤"""
        best_match = None
        best_score = 0.0
        
        for ltm_result in ltm_results:
            # 简单的匹配：检查步骤名称和内容中的相似词
            score = 0.0
            
            if step in ltm_result.content:
                score = 0.8
            elif any(word in ltm_result.content for word in step.split()):
                score = 0.5
            
            score *= ltm_result.relevance_score  # 乘以相关性
            
            if score > best_score:
                best_score = score
                best_match = ltm_result
        
        return best_match if best_score > 0.3 else None
    
    def _create_adaptation_strategy(self, framework_name: str, 
                                    problem_analysis: Dict, 
                                    components: List[Dict]) -> Dict:
        """创建适配策略"""
        strategy = {
            "framework": framework_name,
            "customizations": [],
            "warnings": [],
            "confidence": 0.75
        }
        
        # 根据问题复杂度调整
        if problem_analysis.get("complexity_level") == "high":
            strategy["customizations"].append("增加验证步骤")
            strategy["confidence"] -= 0.1
        
        # 根据所需专业领域调整
        expertise = problem_analysis.get("required_expertise", [])
        for exp in expertise:
            strategy["customizations"].append(f"加强 {exp} 分析")
        
        # 检查是否有来自框架的步骤（可能质量较低）
        framework_steps = sum(1 for c in components if c["source"] == "framework")
        if framework_steps > len(components) / 2:
            strategy["warnings"].append("超过50%的步骤来自框架模板，质量可能不够高")
            strategy["confidence"] -= 0.15
        
        return strategy
    
    def _estimate_composition_quality(self, components: List[Dict], 
                                      ltm_results: List[LTMSearchResult]) -> float:
        """估计组合质量"""
        if not components:
            return 0.0
        
        # 计算平均相关性
        relevances = [c.get("relevance", 0.5) for c in components]
        avg_relevance = sum(relevances) / len(relevances)
        
        # 计算 LTM 支持度（有多少步骤有 LTM 支持）
        ltm_supported = sum(1 for c in components if c["source"] != "framework")
        ltm_support_ratio = ltm_supported / len(components)
        
        # 综合评分
        quality = 0.6 * avg_relevance + 0.4 * ltm_support_ratio
        
        return min(quality, 1.0)

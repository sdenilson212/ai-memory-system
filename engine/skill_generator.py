"""
Skill 自动生成引擎 - Layer 3 实现
用于从零生成新 Skill，当 Layer 1 和 Layer 2 都无法解决问题时使用
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class GenerationStrategy(Enum):
    """生成策略"""
    TEMPLATE_BASED = "template_based"  # 基于模板生成
    ANALOGY = "analogy"  # 类比法生成
    DECOMPOSITION = "decomposition"  # 分解法生成
    HYBRID = "hybrid"  # 混合法生成


@dataclass
class GenerationContext:
    """生成上下文"""
    problem: str
    keywords: List[str]
    domain: str  # "business", "product", "marketing", etc.
    complexity: str  # "low", "medium", "high"
    available_frameworks: List[str]
    ltm_info: Optional[Dict]  # 从 LTM 中能获取的信息
    
    def to_dict(self) -> Dict:
        return {
            "problem": self.problem,
            "keywords": self.keywords,
            "domain": self.domain,
            "complexity": self.complexity,
            "available_frameworks": self.available_frameworks,
            "ltm_info_available": self.ltm_info is not None
        }


@dataclass
class GeneratedSkillDraft:
    """生成的 Skill 草稿"""
    skill_id: str
    name: str
    description: str
    domain: str
    steps: List[Dict]
    rationale: str  # 生成的理由
    generation_strategy: GenerationStrategy
    confidence: float  # 0-1
    needs_verification: bool
    verification_checklist: List[str]
    potential_issues: List[str]
    ltm_references: List[str]  # 引用的 LTM ID
    
    def to_dict(self) -> Dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "steps": self.steps,
            "rationale": self.rationale,
            "generation_strategy": self.generation_strategy.value,
            "confidence": self.confidence,
            "needs_verification": self.needs_verification,
            "verification_checklist": self.verification_checklist,
            "potential_issues": self.potential_issues,
            "ltm_references": self.ltm_references
        }


class SkillGenerator:
    """
    Skill 自动生成引擎
    负责从零生成新 Skill
    """
    
    def __init__(self, ltm_client=None):
        self.ltm = ltm_client
        self.generation_history = []
        
        # 通用的 Skill 模板库
        self.skill_templates = {
            "analysis": {
                "name": "分析框架",
                "steps": ["定义范围", "收集数据", "分析模式", "识别机会", "总结洞察"],
                "description": "用于系统地分析问题或现象"
            },
            "planning": {
                "name": "规划框架",
                "steps": ["设定目标", "分析现状", "识别差距", "制定策略", "执行计划"],
                "description": "用于制定计划和战略"
            },
            "optimization": {
                "name": "优化框架",
                "steps": ["识别瓶颈", "评估改进选项", "优先级排序", "实施改进", "验证效果"],
                "description": "用于优化流程和结果"
            },
            "research": {
                "name": "研究框架",
                "steps": ["明确研究问题", "设计研究方法", "收集证据", "分析数据", "得出结论"],
                "description": "用于进行研究活动"
            },
            "design": {
                "name": "设计框架",
                "steps": ["理解需求", "概念设计", "详细设计", "原型测试", "迭代改进"],
                "description": "用于设计产品或服务"
            }
        }
    
    def can_generate(self, problem: str, available_ltm_info: Optional[Dict] = None) -> Tuple[bool, Dict]:
        """
        判断是否能生成 Skill
        
        Args:
            problem: 问题描述
            available_ltm_info: 可用的 LTM 信息
        
        Returns:
            (能否生成, 评估信息)
        """
        # 基本的可生成性检查
        if not problem or len(problem) < 10:
            return False, {"reason": "Problem description too short"}
        
        # 检查是否有足够的上下文信息
        has_context = available_ltm_info is not None and len(available_ltm_info) > 0
        
        # 评分
        problem_quality_score = self._assess_problem_clarity(problem)
        context_score = 0.7 if has_context else 0.3
        
        generation_feasibility = 0.6 * problem_quality_score + 0.4 * context_score
        
        can_gen = generation_feasibility >= 0.5
        
        return can_gen, {
            "problem_clarity": problem_quality_score,
            "context_availability": context_score,
            "feasibility": generation_feasibility,
            "has_ltm_support": has_context
        }
    
    def analyze_generation_context(self, problem: str, 
                                   available_ltm_info: Optional[Dict] = None) -> GenerationContext:
        """
        分析生成上下文
        
        Args:
            problem: 问题
            available_ltm_info: LTM 信息
        
        Returns:
            GenerationContext
        """
        keywords = self._extract_keywords(problem)
        domain = self._infer_domain(problem, keywords)
        complexity = self._assess_complexity(problem)
        available_frameworks = self._identify_applicable_frameworks(domain, keywords)
        
        return GenerationContext(
            problem=problem,
            keywords=keywords,
            domain=domain,
            complexity=complexity,
            available_frameworks=available_frameworks,
            ltm_info=available_ltm_info
        )
    
    def select_generation_strategy(self, context: GenerationContext) -> GenerationStrategy:
        """
        根据上下文选择生成策略
        
        Args:
            context: 生成上下文
        
        Returns:
            GenerationStrategy
        """
        # 决策树
        if context.ltm_info and len(context.ltm_info) > 5:
            # 有丰富的 LTM 信息，优先用类比法
            return GenerationStrategy.ANALOGY
        elif len(context.available_frameworks) > 0:
            # 有可用框架，用模板法
            return GenerationStrategy.TEMPLATE_BASED
        elif context.complexity == "high":
            # 复杂问题，用分解法
            return GenerationStrategy.DECOMPOSITION
        else:
            # 默认混合法
            return GenerationStrategy.HYBRID
    
    def generate_skill_draft(self, context: GenerationContext, 
                            strategy: GenerationStrategy) -> GeneratedSkillDraft:
        """
        生成 Skill 草稿
        
        Args:
            context: 生成上下文
            strategy: 生成策略
        
        Returns:
            GeneratedSkillDraft
        """
        skill_id = f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        skill_name = self._generate_skill_name(context)
        skill_description = self._generate_skill_description(context)
        
        if strategy == GenerationStrategy.TEMPLATE_BASED:
            steps, rationale, confidence = self._generate_from_template(context)
        elif strategy == GenerationStrategy.ANALOGY:
            steps, rationale, confidence = self._generate_by_analogy(context)
        elif strategy == GenerationStrategy.DECOMPOSITION:
            steps, rationale, confidence = self._generate_by_decomposition(context)
        else:  # HYBRID
            steps, rationale, confidence = self._generate_hybrid(context)
        
        # 生成验证清单
        verification_checklist = self._create_verification_checklist(context, steps)
        
        # 识别潜在问题
        potential_issues = self._identify_potential_issues(context, steps, confidence)
        
        # 提取 LTM 参考
        ltm_references = []
        if context.ltm_info:
            ltm_references = context.ltm_info.get("references", [])
        
        return GeneratedSkillDraft(
            skill_id=skill_id,
            name=skill_name,
            description=skill_description,
            domain=context.domain,
            steps=steps,
            rationale=rationale,
            generation_strategy=strategy,
            confidence=confidence,
            needs_verification=confidence < 0.80,  # 置信度低于0.8需要验证
            verification_checklist=verification_checklist,
            potential_issues=potential_issues,
            ltm_references=ltm_references
        )
    
    # ==================== 生成策略 ====================
    
    def _generate_from_template(self, context: GenerationContext) -> Tuple[List[Dict], str, float]:
        """基于模板生成"""
        # 选择最相关的模板
        best_template = None
        best_score = 0.0
        
        for template_key, template in self.skill_templates.items():
            score = self._match_template_to_domain(template_key, context.domain, context.keywords)
            if score > best_score:
                best_score = score
                best_template = template
        
        if not best_template:
            best_template = self.skill_templates["analysis"]
        
        # 根据问题定制步骤
        steps = []
        for i, step_name in enumerate(best_template["steps"]):
            customization = self._customize_step_for_problem(step_name, context.problem)
            steps.append({
                "step": i + 1,
                "name": step_name,
                "description": customization,
                "source": "template_base"
            })
        
        rationale = f"使用 {best_template['name']} 作为基础，根据问题特征进行定制。"
        confidence = 0.70 + best_score * 0.20  # 模板匹配度越高置信度越高
        
        return steps, rationale, confidence
    
    def _generate_by_analogy(self, context: GenerationContext) -> Tuple[List[Dict], str, float]:
        """基于类比生成"""
        # 从 LTM 中寻找相似的已解决问题
        similar_problems = self._find_similar_problems_in_ltm(context)
        
        if not similar_problems:
            # 回退到模板法
            return self._generate_from_template(context)
        
        # 使用最相似的问题的解决方案作为基础
        base_solution = similar_problems[0].get("solution", {})
        
        # 类比调整（根据不同点进行修改）
        steps = self._adapt_solution_through_analogy(base_solution, context)
        
        rationale = f"通过类比 '{similar_problems[0].get('problem', 'similar_problem')}' 的解决方案生成。"
        confidence = 0.75 + similar_problems[0].get("similarity", 0) * 0.20
        
        return steps, rationale, confidence
    
    def _generate_by_decomposition(self, context: GenerationContext) -> Tuple[List[Dict], str, float]:
        """基于分解法生成"""
        # 将复杂问题分解成子问题
        sub_problems = self._decompose_problem(context.problem)
        
        steps = []
        for i, sub_problem in enumerate(sub_problems):
            sub_step = {
                "step": i + 1,
                "name": f"处理: {sub_problem['aspect']}",
                "description": self._generate_step_for_subproblem(sub_problem),
                "source": "decomposition"
            }
            steps.append(sub_step)
        
        rationale = f"将问题分解为 {len(sub_problems)} 个子问题进行处理: {', '.join(p['aspect'] for p in sub_problems)}"
        confidence = 0.65 + 0.05 * len(sub_problems)  # 子问题越多置信度越低
        confidence = min(confidence, 0.85)
        
        return steps, rationale, confidence
    
    def _generate_hybrid(self, context: GenerationContext) -> Tuple[List[Dict], str, float]:
        """混合法生成"""
        # 结合模板和 LTM 信息
        template_steps, _, template_conf = self._generate_from_template(context)
        
        # 如果有 LTM 信息，用 LTM 信息增强模板步骤
        enhanced_steps = template_steps
        enhancement_count = 0
        
        if context.ltm_info:
            for i, step in enumerate(enhanced_steps):
                ltm_enhancement = self._find_ltm_enhancement_for_step(step["name"], context.ltm_info)
                if ltm_enhancement:
                    step["description"] += f"\n(LTM 建议: {ltm_enhancement})"
                    step["ltm_source"] = ltm_enhancement.get("source")
                    enhancement_count += 1
        
        rationale = f"使用混合法: 模板框架 + {enhancement_count} 处 LTM 增强"
        confidence = template_conf + 0.10 * (enhancement_count / len(template_steps))
        confidence = min(confidence, 0.85)
        
        return enhanced_steps, rationale, confidence
    
    # ==================== 私有方法 ====================
    
    def _assess_problem_clarity(self, problem: str) -> float:
        """评估问题的清晰度"""
        # 简单评估：长度、关键词数量等
        problem_len = len(problem)
        
        if problem_len < 50:
            return 0.4
        elif problem_len < 200:
            return 0.7
        else:
            return 0.9
    
    def _extract_keywords(self, problem: str) -> List[str]:
        """提取关键词"""
        stop_words = {"怎么", "如何", "为什么", "什么", "呢", "吗", "的", "了", "和", "或", "是", "在"}
        words = problem.split()
        keywords = [w for w in words if w not in stop_words and len(w) > 1]
        return keywords[:5]
    
    def _infer_domain(self, problem: str, keywords: List[str]) -> str:
        """推断问题的领域"""
        problem_lower = problem.lower() + " " + " ".join(keywords).lower()
        
        domain_keywords = {
            "business": ["商业", "business", "plan", "计划", "策略", "strategy"],
            "product": ["产品", "product", "feature", "特征", "功能"],
            "marketing": ["营销", "marketing", "推广", "宣传", "用户"],
            "technical": ["技术", "技术", "开发", "代码", "系统"],
            "general": []
        }
        
        for domain, keywords_list in domain_keywords.items():
            if any(kw in problem_lower for kw in keywords_list):
                return domain
        
        return "general"
    
    def _assess_complexity(self, problem: str) -> str:
        """评估复杂度"""
        problem_len = len(problem)
        
        if problem_len < 50:
            return "low"
        elif problem_len < 200:
            return "medium"
        else:
            return "high"
    
    def _identify_applicable_frameworks(self, domain: str, keywords: List[str]) -> List[str]:
        """识别可用框架"""
        applicable = []
        
        framework_domain_map = {
            "analysis": ["all"],
            "planning": ["business", "product"],
            "optimization": ["product", "technical"],
            "research": ["general"],
            "design": ["product"]
        }
        
        for framework, domains in framework_domain_map.items():
            if domain in domains or "all" in domains:
                applicable.append(framework)
        
        return applicable
    
    def _generate_skill_name(self, context: GenerationContext) -> str:
        """生成 Skill 名称"""
        keywords_str = " ".join(context.keywords[:2])
        return f"{keywords_str} 解决方案"
    
    def _generate_skill_description(self, context: GenerationContext) -> str:
        """生成 Skill 描述"""
        return f"用于解决: {context.problem[:100]}..."
    
    def _match_template_to_domain(self, template_key: str, domain: str, keywords: List[str]) -> float:
        """评估模板与领域的匹配度"""
        match_score = 0.5
        
        template_domain_map = {
            "analysis": 0.8 if domain == "general" else 0.6,
            "planning": 0.9 if domain == "business" else 0.5,
            "optimization": 0.9 if domain == "product" else 0.5,
            "research": 0.8 if domain == "general" else 0.4,
            "design": 0.9 if domain == "product" else 0.4
        }
        
        match_score = template_domain_map.get(template_key, 0.5)
        
        return match_score
    
    def _customize_step_for_problem(self, step_name: str, problem: str) -> str:
        """根据问题定制步骤"""
        return f"{step_name}（针对: {problem[:50]}...）"
    
    def _find_similar_problems_in_ltm(self, context: GenerationContext) -> List[Dict]:
        """从 LTM 中查找相似的已解决问题"""
        if not self.ltm:
            return []
        
        # 调用 LTM 搜索
        similar = self.ltm.recall(query=" ".join(context.keywords))
        return similar if similar else []
    
    def _adapt_solution_through_analogy(self, base_solution: Dict, context: GenerationContext) -> List[Dict]:
        """通过类比调整解决方案"""
        if not base_solution:
            # 回退到模板
            template_steps, _, _ = self._generate_from_template(context)
            return template_steps
        
        steps = base_solution.get("steps", [])
        return steps
    
    def _decompose_problem(self, problem: str) -> List[Dict]:
        """分解问题"""
        # 简单的分解：按句子分割
        aspects = []
        sentences = problem.split("。") + problem.split("?")
        
        for i, sentence in enumerate(sentences[:3]):  # 最多分解3个子问题
            if sentence.strip():
                aspects.append({
                    "aspect": sentence.strip()[:30],
                    "index": i
                })
        
        return aspects if aspects else [{"aspect": problem[:30], "index": 0}]
    
    def _generate_step_for_subproblem(self, sub_problem: Dict) -> str:
        """为子问题生成步骤"""
        return f"解决: {sub_problem['aspect']}"
    
    def _create_verification_checklist(self, context: GenerationContext, steps: List[Dict]) -> List[str]:
        """创建验证清单"""
        checklist = [
            "验证步骤逻辑是否连贯",
            "验证输入和输出是否合理",
            "检查是否遗漏关键步骤",
            "确认是否可执行",
            "评估成本和收益"
        ]
        
        if context.complexity == "high":
            checklist.append("进行试点测试")
        
        return checklist
    
    def _identify_potential_issues(self, context: GenerationContext, 
                                   steps: List[Dict], confidence: float) -> List[str]:
        """识别潜在问题"""
        issues = []
        
        if confidence < 0.70:
            issues.append("生成置信度较低，可能需要人工审查")
        
        if not context.ltm_info:
            issues.append("缺乏 LTM 支持，方案可能不够成熟")
        
        if context.complexity == "high":
            issues.append("问题复杂，分解可能不完整")
        
        return issues
    
    def _find_ltm_enhancement_for_step(self, step_name: str, ltm_info: Dict) -> Optional[Dict]:
        """查找 LTM 对步骤的增强信息"""
        enhancements = ltm_info.get("enhancements", [])
        
        for enhancement in enhancements:
            if step_name in enhancement.get("applicable_to", ""):
                return enhancement
        
        return None


# 类型提示修复
from typing import Tuple

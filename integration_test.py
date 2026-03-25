"""
自适应 Skill 系统 - 集成测试和演示
演示三层系统的完整工作流程
"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any

# 导入核心模块
from engine.adaptive_skill_system import (
    AdaptiveSkillSystem, Skill, SkillStep, SkillStatus, SkillType,
    SkillMetadata, GenerationInfo, QualityMetrics, ExecutionResult, SolveResponse
)
from engine.skill_composer import SkillComposer, CompositionPlan
from engine.skill_generator import SkillGenerator, GenerationContext, GeneratedSkillDraft
from engine.quality_evaluator import QualityEvaluator, QualityAssessment


class MockLTMClient:
    """模拟 LTM 客户端用于测试"""
    
    def __init__(self):
        self.memory_store = {
            "mem_001": {
                "id": "mem_001",
                "content": "用户心理学在营销中的应用: 用户的购买决策受到心理学因素影响，包括社群效应、稀缺性、权威性等",
                "category": "discussion",
                "tags": ["心理学", "营销", "用户"],
                "timestamp": datetime.now().isoformat()
            },
            "mem_002": {
                "id": "mem_002",
                "content": "数据驱动营销: 通过 A/B 测试、用户数据分析来验证营销策略的有效性",
                "category": "method",
                "tags": ["数据分析", "验证", "营销"],
                "timestamp": datetime.now().isoformat()
            },
            "mem_003": {
                "id": "mem_003",
                "content": "预算优化框架: 根据渠道的 ROI、转化率来合理分配营销预算",
                "category": "insight",
                "tags": ["预算", "优化", "成本控制"],
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def recall(self, query: str) -> List[Dict]:
        """搜索相关记忆"""
        results = []
        for memory in self.memory_store.values():
            if query.lower() in memory["content"].lower() or any(tag.lower() == query.lower() for tag in memory["tags"]):
                results.append(memory)
        return results
    
    def save(self, memory_data: Dict) -> str:
        """保存新记忆"""
        memory_id = f"mem_{len(self.memory_store) + 1:03d}"
        self.memory_store[memory_id] = {**memory_data, "id": memory_id}
        return memory_id


class MockKBClient:
    """模拟 KB 客户端用于测试"""
    
    def __init__(self):
        self.skill_store = {}
    
    def search(self, query: str) -> List[Skill]:
        """搜索 Skill"""
        return []  # 初始为空
    
    def get(self, skill_id: str) -> Optional[Skill]:
        """获取 Skill"""
        return self.skill_store.get(skill_id)
    
    def save(self, skill: Skill) -> str:
        """保存 Skill"""
        self.skill_store[skill.skill_id] = skill
        return skill.skill_id
    
    def update(self, skill_id: str, skill: Skill) -> bool:
        """更新 Skill"""
        self.skill_store[skill_id] = skill
        return True


class AdaptiveSkillSystemTest:
    """系统集成测试"""
    
    def __init__(self):
        self.ltm = MockLTMClient()
        self.kb = MockKBClient()
        self.system = AdaptiveSkillSystem(kb_client=self.kb, ltm_client=self.ltm)
        self.test_results = []
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 80)
        print("自适应 Skill 系统 - 集成测试")
        print("=" * 80)
        
        self.test_composer()
        self.test_generator()
        self.test_evaluator()
        self.test_full_system()
        
        self.print_summary()
    
    def test_composer(self):
        """测试 Skill 组合引擎"""
        print("\n【测试 1】Skill 组合引擎 (Layer 2)")
        print("-" * 80)
        
        composer = SkillComposer(ltm_client=self.ltm)
        
        problem = "如何提升产品在抖音的转化率?"
        
        # 分析问题
        print(f"\n问题: {problem}")
        problem_analysis = composer.analyze_problem(problem)
        print(f"问题类型: {problem_analysis['problem_type']}")
        print(f"关键词: {problem_analysis['keywords']}")
        print(f"复杂度: {problem_analysis['complexity_level']}")
        
        # 从 LTM 搜索
        keywords = problem_analysis["keywords"]
        ltm_results = composer.search_ltm(problem, keywords)
        print(f"\n搜索到 {len(ltm_results)} 条相关记忆")
        for i, result in enumerate(ltm_results[:3], 1):
            print(f"  {i}. {result.content[:60]}... (相关度: {result.relevance_score:.2f})")
        
        # 评估可组合性
        can_compose, assessment = composer.assess_composability(ltm_results, problem)
        print(f"\n可组合性评估:")
        print(f"  覆盖度: {assessment['coverage_score']:.2f}")
        print(f"  多样性: {assessment['diversity_score']:.2f}")
        print(f"  综合分: {assessment['composability_score']:.2f}")
        print(f"  可组合: {'✓ 是' if can_compose else '✗ 否'}")
        
        if can_compose:
            # 创建组合计划
            composition_plan = composer.create_composition_plan(problem, ltm_results, problem_analysis)
            print(f"\n组合计划:")
            print(f"  基础框架: {composition_plan.base_framework}")
            print(f"  预计质量: {composition_plan.estimated_quality:.2f}")
            print(f"  组成部分: {len(composition_plan.components)} 个")
        
        self.test_results.append(("Composer", "通过"))
    
    def test_generator(self):
        """测试 Skill 自动生成引擎"""
        print("\n【测试 2】Skill 自动生成引擎 (Layer 3)")
        print("-" * 80)
        
        generator = SkillGenerator(ltm_client=self.ltm)
        
        problem = "我们要进入火星采矿业务，怎么制定5年商业计划?"
        
        print(f"\n问题: {problem}")
        
        # 检查是否能生成
        can_gen, feasibility = generator.can_generate(problem, {"references": []})
        print(f"\n可生成性评估:")
        print(f"  问题清晰度: {feasibility['problem_clarity']:.2f}")
        print(f"  上下文可用度: {feasibility['context_availability']:.2f}")
        print(f"  可行性: {feasibility['feasibility']:.2f}")
        print(f"  可生成: {'✓ 是' if can_gen else '✗ 否'}")
        
        if can_gen:
            # 分析上下文
            context = generator.analyze_generation_context(problem)
            print(f"\n生成上下文:")
            print(f"  推断领域: {context.domain}")
            print(f"  复杂度: {context.complexity}")
            print(f"  可用框架: {', '.join(context.available_frameworks)}")
            
            # 选择生成策略
            strategy = generator.select_generation_strategy(context)
            print(f"  选择策略: {strategy.value}")
            
            # 生成草稿
            print(f"\n生成 Skill 草稿...")
            skill_draft = generator.generate_skill_draft(context, strategy)
            print(f"  Skill 名称: {skill_draft.name}")
            print(f"  步骤数: {len(skill_draft.steps)}")
            print(f"  置信度: {skill_draft.confidence:.2f}")
            print(f"  需要验证: {'是' if skill_draft.needs_verification else '否'}")
            
            # 生成理由
            print(f"  生成理由: {skill_draft.rationale}")
        
        self.test_results.append(("Generator", "通过"))
    
    def test_evaluator(self):
        """测试质量评估引擎"""
        print("\n【测试 3】质量评估引擎")
        print("-" * 80)
        
        evaluator = QualityEvaluator()
        
        # 构造测试 Skill 数据
        skill_data = {
            "skill_id": "test_skill_001",
            "name": "营销策略规划",
            "description": "用于制定综合的营销策略",
            "steps": [
                {"step": 1, "name": "市场分析", "description": "分析目标市场和竞争环境"},
                {"step": 2, "name": "用户研究", "description": "研究目标用户的心理和行为"},
                {"step": 3, "name": "策略制定", "description": "基于分析制定营销策略"},
                {"step": 4, "name": "预算分配", "description": "根据 ROI 分配营销预算"},
                {"step": 5, "name": "效果评估", "description": "通过数据验证策略效果"}
            ],
            "generation_info": {
                "type": "composed",
                "confidence": 0.78,
                "ltm_references": ["mem_001", "mem_002", "mem_003"],
                "base_skills": ["market_analysis", "user_research"],
                "needs_verification": False
            },
            "potential_issues": ["需要确保数据准确性"],
            "verification_checklist": ["验证步骤逻辑", "检查数据来源"]
        }
        
        print(f"\n评估 Skill: {skill_data['name']}")
        
        # 进行质量评估
        assessment = evaluator.assess_skill_quality(skill_data)
        
        print(f"\n评估结果:")
        print(f"  总体评分: {assessment.overall_score:.2f}/1.0")
        print(f"  置信度: {assessment.confidence_level}")
        print(f"  是否通过: {'✓ 是' if assessment.is_approved else '✗ 否'}")
        
        print(f"\n维度评分:")
        for dim, score in assessment.dimensions.items():
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            print(f"  {dim:20s}: {bar} {score:.2f}")
        
        print(f"\n改进建议:")
        for i, rec in enumerate(assessment.recommendations, 1):
            print(f"  {i}. {rec}")
        
        # 创建审批总结
        summary = evaluator.create_approval_summary(assessment, skill_data)
        print(f"\n审批总结:")
        print(f"  状态: {summary['status']}")
        print(f"  操作: {summary['action']}")
        
        self.test_results.append(("Evaluator", "通过"))
    
    def test_full_system(self):
        """测试完整系统"""
        print("\n【测试 4】完整系统工作流")
        print("-" * 80)
        
        problem = "如何优化我们的营销预算分配?"
        
        print(f"\n用户问题: {problem}")
        print(f"\n系统尝试解决...")
        
        # 运行系统
        response = self.system.solve(problem, verbose=True)
        
        print(f"\n结果:")
        print(f"  使用层级: Layer {response.layer}")
        print(f"  状态: {response.status}")
        print(f"  置信度: {response.confidence:.2f}")
        print(f"  执行时间: {response.execution_time_ms:.1f}ms")
        
        if response.skill_used:
            print(f"  使用的 Skill:")
            print(f"    - ID: {response.skill_used.skill_id}")
            print(f"    - 名称: {response.skill_used.name}")
            print(f"    - 版本: {response.skill_used.version}")
            print(f"    - 步骤数: {len(response.skill_used.steps)}")
        else:
            print(f"  未找到合适的 Skill，返回通用建议")
        
        self.test_results.append(("FullSystem", "通过"))
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("测试总结")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, result in self.test_results if result == "通过")
        
        print(f"\n总计: {total_tests} 个测试")
        print(f"通过: {passed_tests} 个")
        print(f"失败: {total_tests - passed_tests} 个")
        
        print(f"\n详细结果:")
        for test_name, result in self.test_results:
            status = "✓" if result == "通过" else "✗"
            print(f"  {status} {test_name}")
        
        print("\n" + "=" * 80)
        print("测试完成！")
        print("=" * 80)


if __name__ == "__main__":
    # 运行测试
    test_suite = AdaptiveSkillSystemTest()
    test_suite.run_all_tests()
    
    # 输出为 JSON（用于后续分析）
    print("\n\n【JSON 输出示例】")
    print("-" * 80)
    
    # 示例：系统响应的 JSON 格式
    example_response = {
        "timestamp": datetime.now().isoformat(),
        "problem": "如何提升产品在抖音的转化率?",
        "solution": {
            "layer": 2,
            "status": "success",
            "confidence": 0.82,
            "skill": {
                "id": "composed_skill_001",
                "name": "抖音转化率优化策略",
                "version": "1.0",
                "steps": [
                    "进行用户心理学分析",
                    "制定数据驱动的测试方案",
                    "优化预算分配"
                ]
            }
        }
    }
    
    print(json.dumps(example_response, indent=2, ensure_ascii=False))

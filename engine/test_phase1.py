"""
Phase 1 功能测试

测试内容：
1. Feature List 生成和质量检查
2. Rollback Manager 的 checkpoint 和回滚
3. Execution Agent 的协调执行
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class TestSkill:
    """测试用的 Skill 类"""
    skill_id: str
    version: str
    name: str
    description: str = ""
    steps: List[Dict] = field(default_factory=list)
    
    def to_dict(self):
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "steps": self.steps
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            skill_id=data["skill_id"],
            version=data["version"],
            name=data["name"],
            description=data.get("description", ""),
            steps=data.get("steps", [])
        )


def test_feature_list_generation():
    """测试 Feature List 生成"""
    print("\n" + "=" * 60)
    print("测试1: Feature List 生成")
    print("=" * 60)
    
    from core.feature_list import generate_feature_list
    
    request = "实现一个 Feature List 生成器，用于将用户需求拆解为可追踪的功能点"
    feature_list, info = generate_feature_list(request)
    
    print(f"核心目标: {feature_list.core_objective}")
    print(f"生成信息: {info}")
    print(f"Feature 数量: {len(feature_list.features)}")
    
    assert len(feature_list.features) > 0, "Feature List 不应为空"
    assert feature_list.core_objective, "应有核心目标"
    
    print("\nFeature 详情:")
    for i, f in enumerate(feature_list.features, 1):
        print(f"\n{i}. [{f.feature_id}] {f.description}")
        print(f"   复杂度: {f.complexity.value}")
        print(f"   依赖: {f.dependencies if f.dependencies else '无'}")
        print(f"   验收标准 ({len(f.acceptance_criteria)}条):")
        for ac in f.acceptance_criteria:
            print(f"     - {ac}")
    
    # 测试依赖排序
    print("\n依赖排序结果:")
    ordered = feature_list.get_implementation_order()
    for i, f in enumerate(ordered, 1):
        print(f"{i}. [{f.feature_id}] {f.description[:40]}...")
    
    print("\n[PASS] Feature List 生成测试通过")
    return True


def test_quality_check():
    """测试质量检查"""
    print("\n" + "=" * 60)
    print("测试2: 质量检查")
    print("=" * 60)
    
    from core.feature_list import FeatureListGenerator, Complexity
    
    generator = FeatureListGenerator()
    
    # 测试合格的数据
    good_features = [
        {
            "id": "F001",
            "description": "实现数据结构",
            "acceptance_criteria": ["能序列化", "包含必要字段"],
            "dependencies": [],
            "complexity": "simple"
        }
    ]
    
    result = generator._quality_check(good_features)
    print(f"合格数据检查结果: {result}")
    assert result["passed"], "合格数据应通过检查"
    assert result["score"] >= 0.8, "分数应>=0.8"
    
    # 测试不合格的数据（缺少验收标准）
    bad_features = [
        {
            "id": "F001",
            "description": "实现功能",
            "acceptance_criteria": [],  # 缺少标准
            "dependencies": [],
            "complexity": "simple"
        }
    ]
    
    result = generator._quality_check(bad_features)
    print(f"不合格数据检查结果: {result}")
    assert not result["passed"], "不合格数据不应通过"
    
    print("\n[PASS] 质量检查测试通过")
    return True


def test_rollback_manager():
    """测试 Rollback Manager"""
    print("\n" + "=" * 60)
    print("测试3: Rollback Manager")
    print("=" * 60)
    
    from core.rollback_manager import create_rollback_manager, SideEffect, SideEffectType, RollbackPriority
    
    # 创建 Skill
    skill = TestSkill(
        skill_id="test_skill",
        version="1.0",
        name="测试 Skill",
        steps=[]
    )
    
    # 创建 RollbackManager
    rm = create_rollback_manager()
    
    # 创建 checkpoint
    cp1 = rm.create_checkpoint(skill, "初始版本")
    print(f"创建 checkpoint1: {cp1.checkpoint_id}")
    
    # 修改 Skill
    skill.version = "1.1"
    skill.steps.append({"step": 1, "name": "添加功能1"})
    
    # 记录副作用
    rm.log_side_effect(
        SideEffectType.FILE_CREATED,
        "创建了配置文件",
        RollbackPriority.P1_SHOULD,
        {"file_path": "/tmp/config.txt"}
    )
    
    # 创建新 checkpoint
    cp2 = rm.create_checkpoint(skill, "添加功能1")
    print(f"创建 checkpoint2: {cp2.checkpoint_id}")
    
    # 继续修改
    skill.version = "1.2"
    skill.steps.append({"step": 2, "name": "添加功能2"})
    
    print(f"\n当前状态: 版本={skill.version}, 步骤数={len(skill.steps)}")
    
    # 回滚到 checkpoint1
    print(f"\n回滚到 checkpoint1...")
    result = rm.rollback(skill, target_checkpoint_id=cp1.checkpoint_id)
    
    print(f"回滚结果: {result}")
    assert result["success"], "回滚应成功"
    assert result["p0_rolled_back"], "P0 应已回滚"
    
    print(f"回滚后状态: 版本={skill.version}, 步骤数={len(skill.steps) if skill.steps else 0}")
    # 注意：回滚会恢复到 checkpoint1 时的状态（version=1.0, steps=[]）
    assert skill.version == "1.0", f"版本应回到1.0，实际是{skill.version}"
    assert skill.steps == [] or len(skill.steps) == 0, f"步骤应被清空，实际是{skill.steps}"
    
    # 检查副作用汇总
    summary = rm.get_side_effects_summary(skill.skill_id)
    print(f"\n副作用汇总: {summary}")
    
    print("\n[PASS] Rollback Manager 测试通过")
    return True


def test_execution_agent():
    """测试 Execution Agent"""
    print("\n" + "=" * 60)
    print("测试4: Execution Agent")
    print("=" * 60)
    
    from execution_agent import AdaptiveExecutionEngine
    
    # 创建 Skill
    skill = TestSkill(
        skill_id="execution_test",
        version="1.0",
        name="执行测试 Skill"
    )
    
    # 创建引擎
    engine = AdaptiveExecutionEngine()
    
    # 执行请求
    request = "实现一个功能模块，包含数据结构和算法"
    result = engine.handle_request(request, skill)
    
    print(f"\n执行结果:")
    print(f"成功: {result['success']}")
    print(f"Feature 数量: {result['diagnosis_info']['generation_info']['attempts']}")
    print(f"最终 Skill 版本: {skill.version}")
    print(f"Skill 步骤数: {len(skill.steps)}")
    
    assert result["execution_result"]["summary"]["completed"] > 0, "应至少完成一个 Feature"
    
    print("\n[PASS] Execution Agent 测试通过")
    return True


def test_integration():
    """集成测试"""
    print("\n" + "=" * 60)
    print("测试5: 集成测试")
    print("=" * 60)
    
    from execution_agent import execute_with_feature_list
    
    # 创建 Skill
    skill = TestSkill(
        skill_id="integration_test",
        version="1.0.0",
        name="集成测试 Skill",
        description="用于测试 Phase 1 集成的 Skill"
    )
    
    # 执行复杂请求
    request = "实现一个完整的 Feature List 系统，包括：生成器、质量检查、依赖排序"
    result = execute_with_feature_list(request, skill)
    
    print(f"\n集成测试结果:")
    print(f"请求: {request}")
    print(f"成功: {result['success']}")
    print(f"生成的 Feature 数: {len(result['feature_list']['features'])}")
    print(f"执行摘要: {result['execution_result']['summary']}")
    
    # 验证 Skill 被正确修改
    print(f"\nSkill 最终状态:")
    print(f"版本: {skill.version}")
    print(f"步骤: {len(skill.steps)}")
    for step in skill.steps:
        print(f"  - {step.get('feature_id', '?')}: {step.get('description', '?')[:30]}...")
    
    print("\n[PASS] 集成测试通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Phase 1 功能测试套件")
    print("=" * 60)
    
    tests = [
        ("Feature List 生成", test_feature_list_generation),
        ("质量检查", test_quality_check),
        ("Rollback Manager", test_rollback_manager),
        ("Execution Agent", test_execution_agent),
        ("集成测试", test_integration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n[X] {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"通过: {passed}/{len(tests)}")
    print(f"失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n所有测试通过！Phase 1 功能正常。")
    else:
        print(f"\n有 {failed} 个测试未通过，请检查实现。")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

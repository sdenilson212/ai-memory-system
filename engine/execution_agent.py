"""
Execution Agent 模块 - Phase 1 实现

功能：
1. 接收 Feature List 和执行计划
2. 逐步执行每个 Feature
3. 每个 Feature 完成后自我验证
4. 失败时触发回滚

遵循张大胖建议：
- 诊断 Agent + 执行 Agent 在同一文件中协作
- 接口清晰，但物理上不立即拆分
- 渐进式重构，验证可行后再拆分
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import traceback

# 导入 Feature List 和 Rollback Manager
from core.feature_list import FeatureList, Feature, FeatureStatus, QualityChecker
from core.rollback_manager import RollbackManager, Checkpoint, SideEffect, SideEffectType, RollbackPriority


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"           # 待执行
    IN_PROGRESS = "in_progress"   # 执行中
    COMPLETED = "completed"       # 完成
    FAILED = "failed"             # 失败
    ROLLED_BACK = "rolled_back"   # 已回滚


@dataclass
class ExecutionResult:
    """单个 Feature 的执行结果"""
    feature_id: str
    status: ExecutionStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    implementation_result: Any = None
    verification_result: Optional[Dict] = None
    error_message: Optional[str] = None
    rollback_performed: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "feature_id": self.feature_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "verification_result": self.verification_result,
            "error_message": self.error_message,
            "rollback_performed": self.rollback_performed,
        }


@dataclass
class ExecutionPlan:
    """执行计划"""
    feature_list: FeatureList
    execution_order: List[Feature]  # 按依赖排序后的 Feature 列表
    current_index: int = 0
    results: Dict[str, ExecutionResult] = field(default_factory=dict)
    
    def get_next_feature(self) -> Optional[Feature]:
        """获取下一个待执行的 Feature"""
        if self.current_index < len(self.execution_order):
            feature = self.execution_order[self.current_index]
            self.current_index += 1
            return feature
        return None
    
    def get_current_feature(self) -> Optional[Feature]:
        """获取当前正在执行的 Feature"""
        if 0 < self.current_index <= len(self.execution_order):
            return self.execution_order[self.current_index - 1]
        return None
    
    def record_result(self, result: ExecutionResult):
        """记录执行结果"""
        self.results[result.feature_id] = result
    
    def get_summary(self) -> Dict:
        """获取执行摘要"""
        total = len(self.execution_order)
        completed = sum(1 for r in self.results.values() if r.status == ExecutionStatus.COMPLETED)
        failed = sum(1 for r in self.results.values() if r.status == ExecutionStatus.FAILED)
        rolled_back = sum(1 for r in self.results.values() if r.rollback_performed)
        
        return {
            "total_features": total,
            "completed": completed,
            "failed": failed,
            "rolled_back": rolled_back,
            "progress": f"{completed}/{total}",
            "success_rate": completed / total if total > 0 else 0
        }


class DiagnosisAgent:
    """
    诊断 Agent
    
    职责：
    1. 分析用户需求
    2. 生成 Feature List
    3. 决定执行策略
    
    不处理执行，只处理规划
    """
    
    def __init__(self, feature_list_generator=None):
        from core.feature_list import FeatureListGenerator
        self.feature_generator = feature_list_generator or FeatureListGenerator()
    
    def analyze(self, user_request: str) -> Tuple[FeatureList, Dict]:
        """
        分析用户需求，生成 Feature List
        
        Args:
            user_request: 用户需求
            
        Returns:
            (FeatureList, 分析信息)
        """
        # 生成 Feature List
        feature_list, info = self.feature_generator.generate(user_request)
        
        # 生成执行说明书
        execution_spec = self._create_execution_spec(feature_list)
        
        return feature_list, {
            "generation_info": info,
            "execution_spec": execution_spec
        }
    
    def _create_execution_spec(self, feature_list: FeatureList) -> Dict:
        """
        创建执行说明书
        
        包含：
        - 核心目标
        - Feature List（带优先级和依赖）
        - 关键约束
        - 预期边界情况
        - 验收标准汇总
        """
        # 计算复杂度分布
        complexity_dist = {"simple": 0, "medium": 0, "complex": 0}
        for f in feature_list.features:
            complexity_dist[f.complexity.value] += 1
        
        return {
            "core_objective": feature_list.core_objective,
            "feature_count": len(feature_list.features),
            "complexity_distribution": complexity_dist,
            "implementation_order": [f.feature_id for f in feature_list.get_implementation_order()],
            "key_constraints": [
                "每个 Feature 必须通过自我验证",
                "失败时自动回滚到上一个 checkpoint",
                "遇到未覆盖情况必须停下来询问"
            ],
            "boundary_cases": [
                "Feature 验证失败",
                "依赖的 Feature 失败",
                "回滚失败"
            ],
            "acceptance_criteria_summary": {
                f.feature_id: f.acceptance_criteria 
                for f in feature_list.features
            }
        }


class ExecutionAgent:
    """
    执行 Agent
    
    职责：
    1. 接收 Feature List 和执行说明书
    2. 按顺序执行每个 Feature
    3. 自我验证
    4. 失败时触发回滚
    
    只处理执行，不处理规划
    """
    
    def __init__(self, rollback_manager: Optional[RollbackManager] = None):
        self.rollback_manager = rollback_manager or RollbackManager()
        self.quality_checker = QualityChecker()
        self.execution_handlers: Dict[str, Callable] = {}  # Feature 类型 -> 执行函数
    
    def register_handler(self, feature_type: str, handler: Callable):
        """注册 Feature 类型的执行处理器"""
        self.execution_handlers[feature_type] = handler
    
    def execute(self, feature_list: FeatureList, skill: Any, 
                execution_spec: Optional[Dict] = None) -> Dict:
        """
        执行 Feature List
        
        Args:
            feature_list: Feature List
            skill: 要操作的 Skill 对象
            execution_spec: 执行说明书（可选）
            
        Returns:
            执行结果报告
        """
        # 创建执行计划
        plan = ExecutionPlan(
            feature_list=feature_list,
            execution_order=feature_list.get_implementation_order()
        )
        
        # 创建初始 checkpoint
        checkpoint = self.rollback_manager.create_checkpoint(
            skill, 
            "执行开始前",
            feature_id="initial"
        )
        
        print(f"[ExecutionAgent] 开始执行，共 {len(plan.execution_order)} 个 Feature")
        print(f"[ExecutionAgent] 初始 checkpoint: {checkpoint.checkpoint_id}")
        
        # 逐个执行 Feature
        while True:
            feature = plan.get_next_feature()
            if not feature:
                break
            
            print(f"\n[ExecutionAgent] 执行 Feature: {feature.feature_id}")
            print(f"  描述: {feature.description[:50]}...")
            
            result = self._execute_feature(feature, skill, plan, checkpoint)
            plan.record_result(result)
            
            # 检查是否需要回滚
            if result.status == ExecutionStatus.FAILED and not result.rollback_performed:
                print(f"[ExecutionAgent] Feature {feature.feature_id} 失败，准备回滚")
                rollback_result = self._rollback_to_checkpoint(skill, checkpoint)
                result.rollback_performed = True
                
                if rollback_result["success"]:
                    print(f"[ExecutionAgent] 回滚成功，终止执行")
                    break
                else:
                    print(f"[ExecutionAgent] 回滚失败: {rollback_result['error']}")
                    break
        
        # 生成报告
        summary = plan.get_summary()
        print(f"\n[ExecutionAgent] 执行完成")
        print(f"  完成度: {summary['progress']}")
        print(f"  成功率: {summary['success_rate']:.0%}")
        
        return {
            "success": summary["success_rate"] >= 0.8,
            "summary": summary,
            "results": {k: v.to_dict() for k, v in plan.results.items()},
            "execution_spec": execution_spec
        }
    
    def _execute_feature(self, feature: Feature, skill: Any, 
                        plan: ExecutionPlan, checkpoint: Checkpoint) -> ExecutionResult:
        """
        执行单个 Feature
        
        流程：
        1. 执行实现
        2. 自我验证
        3. 更新 checkpoint
        """
        result = ExecutionResult(
            feature_id=feature.feature_id,
            status=ExecutionStatus.IN_PROGRESS,
            start_time=datetime.now()
        )
        
        try:
            # Step 1: 执行实现
            implementation = self._implement_feature(feature, skill)
            result.implementation_result = implementation
            
            # Step 2: 自我验证
            verification = self._verify_feature(feature, implementation)
            result.verification_result = verification
            
            # Step 3: 判断是否通过
            if verification.get("passed", False):
                result.status = ExecutionStatus.COMPLETED
                
                # 更新 checkpoint
                new_checkpoint = self.rollback_manager.create_checkpoint(
                    skill,
                    f"完成 Feature: {feature.feature_id}",
                    feature_id=feature.feature_id
                )
                
                # 记录副作用
                self.rollback_manager.record_side_effect(
                    new_checkpoint.checkpoint_id,
                    SideEffect(
                        effect_type=SideEffectType.SKILL_MODIFIED,
                        description=f"修改 Skill 以实现 Feature: {feature.feature_id}",
                        priority=RollbackPriority.P0_MUST,
                        timestamp=datetime.now(),
                        metadata={"feature_id": feature.feature_id}
                    )
                )
                
            else:
                result.status = ExecutionStatus.FAILED
                result.error_message = f"验证未通过: {verification.get('details', [])}"
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = f"执行异常: {str(e)}\n{traceback.format_exc()}"
        
        result.end_time = datetime.now()
        return result
    
    def _implement_feature(self, feature: Feature, skill: Any) -> Any:
        """
        实现 Feature
        
        占位符实现 - 实际应根据 Feature 类型调用相应的处理器
        """
        # 尝试找到对应的处理器
        handler = self.execution_handlers.get(feature.complexity.value)
        
        if handler:
            return handler(feature, skill)
        
        # 默认实现：修改 skill 的 steps
        if hasattr(skill, 'steps'):
            skill.steps.append({
                "feature_id": feature.feature_id,
                "description": feature.description,
                "implemented_at": datetime.now().isoformat()
            })
            return f"Added step for {feature.feature_id}"
        
        return f"Mock implementation for {feature.feature_id}"
    
    def _verify_feature(self, feature: Feature, implementation: Any) -> Dict:
        """
        自我验证 Feature
        
        Phase 1: 自我验证（简单实现）
        Phase 3+: 可升级为独立 Evaluator
        """
        return self.quality_checker.check_feature(feature, implementation)
    
    def _rollback_to_checkpoint(self, skill: Any, checkpoint: Checkpoint) -> Dict:
        """回滚到指定 checkpoint"""
        return self.rollback_manager.rollback(skill, target_checkpoint_id=checkpoint.checkpoint_id)
    
    def handle_uncovered_case(self, situation: str, context: Dict) -> Dict:
        """
        处理未覆盖情况
        
        原则：停下来问，不要自己猜
        """
        return {
            "action": "ASK",
            "message": f"遇到未覆盖情况: {situation}",
            "context": context,
            "suggestions": [
                "请提供指导如何处理这种情况",
                "或者将此情况加入处理规则"
            ]
        }


class AdaptiveExecutionEngine:
    """
    自适应执行引擎
    
    协调 DiagnosisAgent 和 ExecutionAgent
    提供统一的执行接口
    """
    
    def __init__(self):
        self.diagnosis_agent = DiagnosisAgent()
        self.execution_agent = ExecutionAgent()
        
        # 执行历史
        self.execution_history: List[Dict] = []
    
    def handle_request(self, user_request: str, skill: Any) -> Dict:
        """
        处理用户请求（完整流程）
        
        Args:
            user_request: 用户需求
            skill: 要操作的 Skill 对象
            
        Returns:
            处理结果
        """
        print("=" * 60)
        print("[AdaptiveExecutionEngine] 开始处理请求")
        print(f"请求: {user_request[:50]}...")
        print("=" * 60)
        
        # Step 1: 诊断 Agent 分析
        print("\n[阶段1] DiagnosisAgent 分析需求...")
        feature_list, diagnosis_info = self.diagnosis_agent.analyze(user_request)
        
        print(f"生成 Feature List: {len(feature_list.features)} 个 Feature")
        print(f"核心目标: {feature_list.core_objective}")
        
        # Step 2: Execution Agent 执行
        print("\n[阶段2] ExecutionAgent 执行...")
        execution_result = self.execution_agent.execute(
            feature_list, 
            skill,
            execution_spec=diagnosis_info.get("execution_spec")
        )
        
        # 记录历史
        self.execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "request": user_request,
            "feature_count": len(feature_list.features),
            "result": execution_result
        })
        
        print("\n" + "=" * 60)
        print("[AdaptiveExecutionEngine] 处理完成")
        print("=" * 60)
        
        return {
            "success": execution_result["success"],
            "feature_list": feature_list.to_dict(),
            "diagnosis_info": diagnosis_info,
            "execution_result": execution_result
        }


# 便捷函数
def execute_with_feature_list(user_request: str, skill: Any) -> Dict:
    """
    便捷函数：使用 Feature List 执行请求
    
    Args:
        user_request: 用户需求
        skill: Skill 对象
        
    Returns:
        执行结果
    """
    engine = AdaptiveExecutionEngine()
    return engine.handle_request(user_request, skill)


if __name__ == "__main__":
    # 测试
    from dataclasses import dataclass, field
    
    @dataclass
    class TestSkill:
        skill_id: str
        version: str
        name: str
        steps: List[Dict] = field(default_factory=list)
        
        def to_dict(self):
            return {
                "skill_id": self.skill_id,
                "version": self.version,
                "name": self.name,
                "steps": self.steps
            }
        
        @classmethod
        def from_dict(cls, data):
            return cls(
                skill_id=data["skill_id"],
                version=data["version"],
                name=data["name"],
                steps=data.get("steps", [])
            )
    
    # 创建测试 Skill
    skill = TestSkill(
        skill_id="test_skill",
        version="1.0",
        name="测试 Skill"
    )
    
    # 执行请求
    result = execute_with_feature_list(
        "实现一个 Feature List 生成器，用于将用户需求拆解为可追踪的功能点",
        skill
    )
    
    print("\n最终 Skill 状态:")
    print(f"版本: {skill.version}")
    print(f"步骤数: {len(skill.steps)}")
    print(f"步骤: {skill.steps}")

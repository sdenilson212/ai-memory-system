"""
自适应 Skill 系统 - 核心执行引擎
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class SkillStatus(Enum):
    """Skill 的状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class SkillType(Enum):
    """Skill 的生成方式"""
    MANUAL = "manual"
    COMPOSED = "composed"
    AUTO_GENERATED = "auto-generated"


@dataclass
class SkillStep:
    """Skill 中的单个步骤"""
    step_number: int
    name: str
    description: str
    source: str  # "框架" | "记忆" | "自动生成"
    customization: Optional[str] = None
    estimated_duration: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "step": self.step_number,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "customization": self.customization,
            "estimated_duration": self.estimated_duration
        }


@dataclass
class SkillMetadata:
    """Skill 的元数据"""
    created_at: datetime
    updated_at: datetime
    created_by: str  # "user" | "ai-generated"
    update_reason: Optional[str] = None
    last_challenged_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "update_reason": self.update_reason,
            "last_challenged_at": self.last_challenged_at.isoformat() if self.last_challenged_at else None
        }


@dataclass
class GenerationInfo:
    """自动生成相关的信息"""
    skill_type: SkillType
    base_skills: List[str] = field(default_factory=list)
    ltm_references: List[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_verification: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "type": self.skill_type.value,
            "base_skills": self.base_skills,
            "ltm_references": self.ltm_references,
            "confidence": self.confidence,
            "needs_verification": self.needs_verification
        }


@dataclass
class QualityMetrics:
    """Skill 的质量指标"""
    usage_count: int = 0
    success_rate: float = 0.0  # 0-1
    user_satisfaction: float = 0.0  # 1-5
    failure_count: int = 0
    total_failures: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "user_satisfaction": self.user_satisfaction,
            "failure_count": self.failure_count,
            "total_failures": self.total_failures
        }


@dataclass
class Skill:
    """Skill 的完整定义"""
    skill_id: str
    name: str
    description: str
    version: str
    status: SkillStatus
    
    # 内容
    steps: List[SkillStep]
    required_inputs: List[str]
    outputs: List[str]
    parameters: Dict[str, Any]
    
    # 元数据
    metadata: SkillMetadata
    generation_info: GenerationInfo
    quality_metrics: QualityMetrics
    
    # 版本历史
    versions: Dict[str, Dict] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典（用于存储）"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "status": self.status.value,
            "steps": [step.to_dict() for step in self.steps],
            "required_inputs": self.required_inputs,
            "outputs": self.outputs,
            "parameters": self.parameters,
            "metadata": self.metadata.to_dict(),
            "generation_info": self.generation_info.to_dict(),
            "quality_metrics": self.quality_metrics.to_dict(),
            "versions": self.versions
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Skill':
        """从字典创建 Skill"""
        steps = [
            SkillStep(
                step_number=step['step'],
                name=step['name'],
                description=step['description'],
                source=step['source'],
                customization=step.get('customization'),
                estimated_duration=step.get('estimated_duration')
            )
            for step in data['steps']
        ]
        
        metadata = SkillMetadata(
            created_at=datetime.fromisoformat(data['metadata']['created_at']),
            updated_at=datetime.fromisoformat(data['metadata']['updated_at']),
            created_by=data['metadata']['created_by'],
            update_reason=data['metadata'].get('update_reason'),
            last_challenged_at=datetime.fromisoformat(data['metadata']['last_challenged_at']) 
                if data['metadata'].get('last_challenged_at') else None
        )
        
        generation_info = GenerationInfo(
            skill_type=SkillType(data['generation_info']['type']),
            base_skills=data['generation_info'].get('base_skills', []),
            ltm_references=data['generation_info'].get('ltm_references', []),
            confidence=data['generation_info'].get('confidence', 0.0),
            needs_verification=data['generation_info'].get('needs_verification', False)
        )
        
        quality_metrics = QualityMetrics(
            usage_count=data['quality_metrics'].get('usage_count', 0),
            success_rate=data['quality_metrics'].get('success_rate', 0.0),
            user_satisfaction=data['quality_metrics'].get('user_satisfaction', 0.0),
            failure_count=data['quality_metrics'].get('failure_count', 0),
            total_failures=data['quality_metrics'].get('total_failures', 0)
        )
        
        return cls(
            skill_id=data['skill_id'],
            name=data['name'],
            description=data['description'],
            version=data['version'],
            status=SkillStatus(data['status']),
            steps=steps,
            required_inputs=data['required_inputs'],
            outputs=data['outputs'],
            parameters=data['parameters'],
            metadata=metadata,
            generation_info=generation_info,
            quality_metrics=quality_metrics,
            versions=data.get('versions', {})
        )


@dataclass
class ExecutionResult:
    """Skill 执行的结果"""
    success: bool
    output: Any
    duration_seconds: float
    steps_completed: int
    total_steps: int
    error_message: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "duration_seconds": self.duration_seconds,
            "steps_completed": self.steps_completed,
            "total_steps": self.total_steps,
            "error_message": self.error_message,
            "metadata": self.metadata
        }


@dataclass
class SolveResponse:
    """系统解决问题的最终响应"""
    result: Any
    skill_used: Optional[Skill]
    layer: int  # 1 | 2 | 3 | 0
    status: str  # "success" | "partial" | "failed"
    confidence: float  # 0-1
    execution_time_ms: float
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "result": self.result,
            "skill": self.skill_used.to_dict() if self.skill_used else None,
            "layer": self.layer,
            "status": self.status,
            "confidence": self.confidence,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata
        }


class SkillExecutor:
    """Skill 执行引擎"""
    
    def __init__(self):
        self.execution_history = []
    
    def execute(self, skill: Skill, problem: str, inputs: Optional[Dict] = None) -> ExecutionResult:
        """
        执行一个 Skill
        
        Args:
            skill: 要执行的 Skill
            problem: 原始问题
            inputs: 输入参数
        
        Returns:
            ExecutionResult: 执行结果
        """
        import time
        start_time = time.time()
        
        try:
            steps_completed = 0
            outputs = []
            
            # 按顺序执行每个步骤
            for step in skill.steps:
                try:
                    # 这里是 Skill 执行的关键逻辑
                    # 实际应用中需要根据 step.source 调用不同的处理器
                    step_result = self._execute_step(step, problem, inputs, outputs)
                    outputs.append(step_result)
                    steps_completed += 1
                except Exception as e:
                    return ExecutionResult(
                        success=False,
                        output=None,
                        duration_seconds=time.time() - start_time,
                        steps_completed=steps_completed,
                        total_steps=len(skill.steps),
                        error_message=f"Step {step.name} failed: {str(e)}"
                    )
            
            # 整合最终输出
            final_output = self._aggregate_outputs(outputs, skill.outputs)
            
            execution_time = time.time() - start_time
            result = ExecutionResult(
                success=True,
                output=final_output,
                duration_seconds=execution_time,
                steps_completed=steps_completed,
                total_steps=len(skill.steps),
                metadata={
                    "skill_id": skill.skill_id,
                    "skill_version": skill.version,
                    "step_details": [step.name for step in skill.steps]
                }
            )
            
            # 记录到历史
            self.execution_history.append({
                "timestamp": datetime.now(),
                "skill_id": skill.skill_id,
                "result": result.to_dict()
            })
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                output=None,
                duration_seconds=execution_time,
                steps_completed=0,
                total_steps=len(skill.steps),
                error_message=f"Skill execution failed: {str(e)}"
            )
    
    def _execute_step(self, step: SkillStep, problem: str, inputs: Optional[Dict], 
                      previous_outputs: List) -> Any:
        """执行单个步骤"""
        # 这是一个占位符，实际实现需要根据 step.source 调用不同的处理器
        
        if step.source == "框架":
            # 调用框架逻辑
            return self._execute_framework_step(step, problem, inputs, previous_outputs)
        elif step.source == "记忆":
            # 从 LTM 中获取并执行
            return self._execute_memory_step(step, problem, inputs, previous_outputs)
        elif step.source == "自动生成":
            # 执行自动生成的步骤
            return self._execute_generated_step(step, problem, inputs, previous_outputs)
        else:
            raise ValueError(f"Unknown step source: {step.source}")
    
    def _execute_framework_step(self, step: SkillStep, problem: str, 
                               inputs: Optional[Dict], previous_outputs: List) -> Any:
        """执行基于框架的步骤"""
        # 占位符实现
        return {
            "step_name": step.name,
            "status": "completed",
            "message": f"Framework step '{step.name}' executed"
        }
    
    def _execute_memory_step(self, step: SkillStep, problem: str, 
                            inputs: Optional[Dict], previous_outputs: List) -> Any:
        """执行基于记忆的步骤"""
        # 占位符实现
        return {
            "step_name": step.name,
            "status": "completed",
            "message": f"Memory-based step '{step.name}' executed"
        }
    
    def _execute_generated_step(self, step: SkillStep, problem: str, 
                               inputs: Optional[Dict], previous_outputs: List) -> Any:
        """执行自动生成的步骤"""
        # 占位符实现
        return {
            "step_name": step.name,
            "status": "completed",
            "message": f"Auto-generated step '{step.name}' executed"
        }
    
    def _aggregate_outputs(self, outputs: List, output_specs: List[str]) -> Dict:
        """整合多个步骤的输出"""
        aggregated = {}
        for i, output_spec in enumerate(output_specs):
            if i < len(outputs):
                aggregated[output_spec] = outputs[i]
        return aggregated


class AdaptiveSkillSystem:
    """自适应 Skill 系统的核心类"""
    
    def __init__(self, kb_client=None, ltm_client=None, memory_dir=None):
        """
        初始化系统
        
        Args:
            kb_client: 知识库客户端（如果为 None，将尝试从 memory_dir 创建）
            ltm_client: 长期记忆客户端（如果为 None，将尝试从 memory_dir 创建）
            memory_dir: 记忆系统目录路径
        """
        if kb_client is None and ltm_client is None and memory_dir is None:
            # 尝试从配置获取默认路径
            try:
                import sys
                import os
                from pathlib import Path
                
                # 查找 memory_dir
                possible_paths = [
                    Path.cwd() / "memory-bank",
                    Path(__file__).parent.parent / "memory-bank",
                    Path.home() / ".ai-memory-system" / "memory-bank"
                ]
                
                for path in possible_paths:
                    if path.exists():
                        memory_dir = str(path)
                        break
            except Exception as e:
                logger.warning(f"自动检测记忆目录失败: {e}")
                memory_dir = None
        
        # 创建记忆客户端
        if memory_dir:
            from .memory_system_client import MemorySystemClient
            self.memory_client = MemorySystemClient(memory_dir)
            self.kb = self.memory_client.kb
            self.ltm = self.memory_client.ltm
        else:
            self.memory_client = None
            self.kb = kb_client
            self.ltm = ltm_client
        
        self.executor = SkillExecutor()
        self.skills_cache = {}  # 本地 Skill 缓存
        self.skill_composer = None
        self.skill_generator = None
        self.quality_evaluator = None
        
        # 延迟初始化子模块
        self._initialize_submodules()
    
    def _initialize_submodules(self):
        """初始化子模块（延迟加载）"""
        try:
            from .skill_composer import SkillComposer
            from .skill_generator import SkillGenerator
            from .quality_evaluator import QualityEvaluator
            
            self.skill_composer = SkillComposer(ltm_client=self.ltm, kb_client=self.kb)
            self.skill_generator = SkillGenerator(ltm_client=self.ltm)
            self.quality_evaluator = QualityEvaluator()
            
            # 注：SkillGenerator 预期有 set_composer 方法用于组合，但当前版本尚未实现
            # 暂时注释掉这个连接
            
        except ImportError as e:
            print(f"警告：无法加载子模块，部分功能不可用：{e}")
    
    def solve(self, problem: str, verbose: bool = False) -> SolveResponse:
        """
        主入口：尝试解决用户的问题
        
        Args:
            problem: 用户的问题
            verbose: 是否输出详细信息
        
        Returns:
            SolveResponse: 完整的解决方案响应
        """
        import time
        start_time = time.time()
        
        # 第一层：直接调用
        if verbose:
            print("[Layer 1] 搜索已有 Skill...")
        result_1, skill_1 = self._try_layer_1(problem)
        if result_1:
            return SolveResponse(
                result=result_1.output,
                skill_used=skill_1,
                layer=1,
                status="success",
                confidence=0.95,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={"layer_1_direct_match": True}
            )
        
        # 第二层：组合
        if verbose:
            print("[Layer 2] 尝试从记忆中组合 Skill...")
        result_2, skill_2 = self._try_layer_2(problem)
        if result_2:
            return SolveResponse(
                result=result_2.output,
                skill_used=skill_2,
                layer=2,
                status="success",
                confidence=0.80,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={"layer_2_composed": True}
            )
        
        # 第三层：自动生成
        if verbose:
            print("[Layer 3] 尝试自动生成 Skill...")
        result_3, skill_3, gen_info = self._try_layer_3(problem)
        if result_3:
            quality_score = gen_info.get("quality", 0)
            status = "success" if quality_score >= 0.75 else "partial"
            confidence = quality_score
            
            return SolveResponse(
                result=result_3.output,
                skill_used=skill_3,
                layer=3,
                status=status,
                confidence=confidence,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={
                    "layer_3_auto_generated": True,
                    "generation_quality": quality_score,
                    "needs_feedback": quality_score < 0.85
                }
            )
        
        # 都失败了
        return SolveResponse(
            result=None,
            skill_used=None,
            layer=0,
            status="failed",
            confidence=0,
            execution_time_ms=(time.time() - start_time) * 1000,
            metadata={"reason": "Cannot solve this problem with current skills"}
        )
    
    def _try_layer_1(self, problem: str) -> Tuple[Optional[ExecutionResult], Optional[Skill]]:
        """第一层：直接调用已有 Skill"""
        # 这里需要与真实的 KB 客户端集成
        # 目前是占位符实现
        return None, None
    
    def _try_layer_2(self, problem: str) -> Tuple[Optional[ExecutionResult], Optional[Skill]]:
        """第二层：从记忆中组合"""
        from .skill_composer import SkillComposer
        
        composer = SkillComposer(ltm_client=self.ltm, kb_client=self.kb)
        
        # 分析问题
        problem_analysis = composer.analyze_problem(problem)
        
        # 从 LTM 搜索
        keywords = problem_analysis.get("keywords", [])
        ltm_results = composer.search_ltm(problem, keywords)
        
        # 评估是否能组合
        can_compose, assessment = composer.assess_composability(ltm_results, problem)
        if not can_compose:
            return None, None
        
        # 创建组合计划
        composition_plan = composer.create_composition_plan(problem, ltm_results, problem_analysis)
        
        # 根据组合计划创建 Skill
        composed_skill = self._skill_from_composition_plan(composition_plan, problem)
        
        # 执行 Skill
        result = self.executor.execute(composed_skill, problem)
        
        return result, composed_skill
    
    def _try_layer_3(self, problem: str) -> Tuple[Optional[ExecutionResult], Optional[Skill], Optional[Dict]]:
        """第三层：自动生成"""
        from .skill_generator import SkillGenerator
        from .quality_evaluator import QualityEvaluator
        
        generator = SkillGenerator(ltm_client=self.ltm)
        evaluator = QualityEvaluator()
        
        # 检查是否能生成
        available_ltm_info = self.ltm.recall(query=problem) if self.ltm else None
        can_gen, gen_feasibility = generator.can_generate(problem, available_ltm_info)
        
        if not can_gen:
            return None, None, None
        
        # 分析生成上下文
        context = generator.analyze_generation_context(problem, available_ltm_info)
        
        # 选择生成策略
        strategy = generator.select_generation_strategy(context)
        
        # 生成草稿
        skill_draft = generator.generate_skill_draft(context, strategy)
        
        # 质量评估
        assessment = evaluator.assess_skill_quality(skill_draft.to_dict())
        
        # 如果质量不够好，返回部分成功
        if not assessment.is_approved:
            return None, None, {
                "quality": assessment.overall_score,
                "confidence": assessment.confidence_level,
                "recommendations": assessment.recommendations
            }
        
        # 将草稿转换为完整 Skill
        generated_skill = self._skill_from_draft(skill_draft)
        
        # 执行 Skill
        result = self.executor.execute(generated_skill, problem)
        
        return result, generated_skill, {
            "quality": assessment.overall_score,
            "confidence": assessment.confidence_level,
            "strategy": strategy.value,
            "generation_info": skill_draft.to_dict()
        }
    
    def update_skill_from_feedback(self, skill_id: str, feedback: str) -> Skill:
        """
        根据用户反馈更新 Skill
        
        Args:
            skill_id: Skill ID
            feedback: 用户反馈
        
        Returns:
            更新后的 Skill
        """
        # 获取原有 Skill
        skill = self.skills_cache.get(skill_id)
        if not skill and self.kb:
            skill = self.kb.get(skill_id)
        
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")
        
        # 分析反馈
        feedback_analysis = self._analyze_feedback(feedback)
        
        # 更新 Skill
        updated_skill = self._update_skill(skill, feedback_analysis)
        
        # 保存更新
        if self.kb:
            self.kb.update(skill_id, updated_skill)
        
        self.skills_cache[skill_id] = updated_skill
        
        # 记录到 LTM
        if self.ltm:
            self.ltm.save({
                "content": f"Skill '{skill.name}' updated: {feedback}",
                "category": "project",
                "tags": ["skill-update", skill_id]
            })
        
        return updated_skill
    
    def _analyze_feedback(self, feedback: str) -> Dict:
        """分析用户反馈"""
        # 占位符实现
        return {
            "sentiment": "neutral",
            "aspect": "general",
            "suggestion": feedback
        }
    
    def _update_skill(self, skill: Skill, feedback_analysis: Dict) -> Skill:
        """根据反馈更新 Skill"""
        # 更新元数据
        skill.metadata.updated_at = datetime.now()
        skill.metadata.update_reason = feedback_analysis["suggestion"]
        skill.metadata.last_challenged_at = datetime.now()
        
        # 更新版本
        old_version = skill.version
        major, minor = map(int, old_version.split('.')[:2])
        minor += 1
        skill.version = f"{major}.{minor}"
        
        # 记录到版本历史
        skill.versions[old_version] = {
            "timestamp": datetime.now().isoformat(),
            "reason": feedback_analysis["suggestion"]
        }
        
        return skill
    
    def _skill_from_composition_plan(self, composition_plan: Any, problem: str) -> Skill:
        """从组合计划创建 Skill"""
        skill_id = f"composed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        steps = []
        for i, component in enumerate(composition_plan.components):
            step = SkillStep(
                step_number=i + 1,
                name=component.get("step", f"Step {i + 1}"),
                description=component.get("aspect", ""),
                source="记忆" if component["source"] != "framework" else "框架",
                customization=f"根据问题调整: {problem[:50]}"
            )
            steps.append(step)
        
        adaptation_strategy = composition_plan.adaptation_strategy
        
        skill = Skill(
            skill_id=skill_id,
            name=f"组合 Skill: {problem[:30]}",
            description=f"从 {len([c for c in composition_plan.components if c['source'] != 'framework'])} 个 LTM 源组合生成",
            version="1.0",
            status=SkillStatus.EXPERIMENTAL,
            steps=steps,
            required_inputs=[],
            outputs=["result"],
            parameters={"adaptation_strategy": adaptation_strategy},
            metadata=SkillMetadata(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by="ai-generated"
            ),
            generation_info=GenerationInfo(
                skill_type=SkillType.COMPOSED,
                ltm_references=[c.get("source") for c in composition_plan.components if c["source"] != "framework"],
                confidence=composition_plan.estimated_quality,
                needs_verification=composition_plan.estimated_quality < 0.80
            ),
            quality_metrics=QualityMetrics()
        )
        
        return skill
    
    def _skill_from_draft(self, skill_draft: Any) -> Skill:
        """从生成的草稿创建完整 Skill"""
        steps = []
        for step_data in skill_draft.steps:
            step = SkillStep(
                step_number=step_data.get("step", 0),
                name=step_data.get("name", ""),
                description=step_data.get("description", ""),
                source=step_data.get("source", "自动生成")
            )
            steps.append(step)
        
        skill = Skill(
            skill_id=skill_draft.skill_id,
            name=skill_draft.name,
            description=skill_draft.description,
            version="1.0-beta",
            status=SkillStatus.EXPERIMENTAL,
            steps=steps,
            required_inputs=[],
            outputs=["result"],
            parameters={
                "strategy": skill_draft.generation_strategy.value,
                "verification_checklist": skill_draft.verification_checklist
            },
            metadata=SkillMetadata(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by="ai-generated",
                update_reason=f"自动生成: {skill_draft.rationale}"
            ),
            generation_info=GenerationInfo(
                skill_type=SkillType.AUTO_GENERATED,
                ltm_references=skill_draft.ltm_references,
                confidence=skill_draft.confidence,
                needs_verification=skill_draft.needs_verification
            ),
            quality_metrics=QualityMetrics()
        )
        
        return skill


if __name__ == "__main__":
    # 示例：创建并执行一个 Skill
    
    # 创建一个简单的 Skill
    skill = Skill(
        skill_id="skill-demo-001",
        name="Demo Skill",
        description="A simple demo skill",
        version="1.0",
        status=SkillStatus.ACTIVE,
        steps=[
            SkillStep(
                step_number=1,
                name="Step 1",
                description="First step",
                source="框架"
            ),
            SkillStep(
                step_number=2,
                name="Step 2",
                description="Second step",
                source="记忆"
            )
        ],
        required_inputs=["input1", "input2"],
        outputs=["output1"],
        parameters={},
        metadata=SkillMetadata(
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by="user"
        ),
        generation_info=GenerationInfo(
            skill_type=SkillType.MANUAL
        ),
        quality_metrics=QualityMetrics()
    )
    
    # 执行 Skill
    executor = SkillExecutor()
    result = executor.execute(skill, "Demo problem")
    print(json.dumps(result.to_dict(), indent=2, default=str))
    
    # 创建系统并测试
    system = AdaptiveSkillSystem()
    response = system.solve("How to solve this problem?", verbose=True)
    print(json.dumps(response.to_dict(), indent=2, default=str))

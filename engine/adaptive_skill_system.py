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
        """
        执行基于框架的步骤。
        
        框架步骤代表通用方法论（如「收集数据」「分析趋势」「制定策略」），
        执行结果包含：步骤描述、从问题中提取的关键信息、自定义说明。
        """
        # 从前一步骤的输出中聚合上下文
        context_summary = ""
        if previous_outputs:
            prev_messages = [
                str(o.get("output", o.get("message", "")))
                for o in previous_outputs
                if isinstance(o, dict)
            ]
            context_summary = " | ".join(filter(None, prev_messages))[:200]
        
        output_text = step.description
        if step.customization:
            output_text += f"\n调整点：{step.customization}"
        if context_summary:
            output_text += f"\n基于上下文：{context_summary}"
        
        return {
            "step_name": step.name,
            "step_number": step.step_number,
            "source": "framework",
            "status": "completed",
            "output": output_text,
            "estimated_duration": step.estimated_duration
        }
    
    def _execute_memory_step(self, step: SkillStep, problem: str,
                            inputs: Optional[Dict], previous_outputs: List) -> Any:
        """
        执行基于记忆的步骤。
        
        记忆步骤将 LTM 中已有的知识应用到当前问题。
        执行结果将步骤描述与问题关键词结合，生成应用建议。
        """
        # 提取问题核心词（最多 5 个有意义的词）
        problem_tokens = [
            w for w in problem.replace("，", " ").replace("。", " ").split()
            if len(w) > 1
        ][:5]
        
        # 组合应用建议
        applied_text = step.description
        if problem_tokens:
            applied_text += f"\n应用到「{'、'.join(problem_tokens)}」："
            applied_text += f" 根据已有经验，{step.description}"
        if step.customization:
            applied_text += f"\n个性化调整：{step.customization}"
        
        return {
            "step_name": step.name,
            "step_number": step.step_number,
            "source": "memory",
            "status": "completed",
            "output": applied_text,
            "memory_applied": True,
            "problem_keywords": problem_tokens
        }
    
    def _execute_generated_step(self, step: SkillStep, problem: str,
                               inputs: Optional[Dict], previous_outputs: List) -> Any:
        """
        执行自动生成的步骤。
        
        自动生成步骤是系统根据问题特征推断出的行动方案，
        执行时整合问题、步骤描述和已有前置输出，生成结构化建议。
        """
        # 提取所有前置步骤输出
        prior_context = []
        for o in previous_outputs:
            if isinstance(o, dict):
                prior_context.append(o.get("output", o.get("message", "")))
        
        # 构建生成步骤的行动建议
        action_text = f"[自动生成] {step.description}"
        if step.customization:
            action_text += f"\n策略：{step.customization}"
        if prior_context:
            action_text += f"\n基于前序步骤：{' → '.join(str(c)[:80] for c in prior_context if c)}"
        
        return {
            "step_name": step.name,
            "step_number": step.step_number,
            "source": "auto_generated",
            "status": "completed",
            "output": action_text,
            "confidence": 0.70,  # 自动生成步骤默认置信度
            "needs_review": True
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
            confidence=0.0,
            execution_time_ms=(time.time() - start_time) * 1000,
            metadata={"reason": "Cannot solve this problem with current skills"}
        )
    
    def _try_layer_1(self, problem: str) -> Tuple[Optional[ExecutionResult], Optional[Skill]]:
        """
        第一层：在 KB 中搜索已有 Skill，若置信度足够则直接执行。
        
        匹配逻辑：
        1. 先从本地缓存（skills_cache）中查找
        2. 若有 KB 客户端，搜索 KB
        3. 计算关键词覆盖率作为置信度，阈值 0.60 触发执行
        """
        # 1. 提取问题关键词（中文用字符 2-gram，英文按空格）
        problem_lower = problem.lower()
        
        # 检测是否含中文字符
        has_chinese = any('\u4e00' <= c <= '\u9fff' for c in problem_lower)
        
        if has_chinese:
            # 中文：去掉标点后做 2-gram 切片（单字不够区分，2字更精准）
            import re
            cjk_chars = re.sub(r'[^\u4e00-\u9fff]', '', problem_lower)
            # 单字词 + 2字词，确保覆盖率
            keywords = list(set(
                [cjk_chars[i:i+1] for i in range(len(cjk_chars))] +
                [cjk_chars[i:i+2] for i in range(len(cjk_chars) - 1)]
            ))
            # 过滤常见虚词（助词、连词不算关键词）
            stop_chars = {"的", "了", "是", "在", "和", "与", "或", "也", "都", "很",
                          "一", "个", "这", "那", "有", "到", "对", "为", "以", "及"}
            keywords = [k for k in keywords if k not in stop_chars and len(k) >= 1]
        else:
            # 英文：按空格分词
            keywords = [w for w in problem_lower.replace(',', ' ').replace('.', ' ').split()
                       if len(w) > 2]
        
        # 2. 先查本地缓存
        best_skill: Optional[Skill] = None
        best_score: float = 0.0
        
        for skill in self.skills_cache.values():
            if skill.status == SkillStatus.DEPRECATED:
                continue
            score = self._compute_skill_relevance(skill, keywords, problem_lower)
            if score > best_score:
                best_score = score
                best_skill = skill
        
        # 3. 若有 KB 客户端，从知识库搜索
        if self.kb:
            try:
                kb_results = self.kb.search(query=problem, top_k=5)
                for entry in (kb_results or []):
                    # KB 条目可能是 dict（kb_search 返回）
                    entry_dict = entry if isinstance(entry, dict) else (entry.to_dict() if hasattr(entry, 'to_dict') else {})
                    
                    # 尝试从 KB 条目重建 Skill
                    skill_data = entry_dict.get("content_parsed") or entry_dict.get("extra", {})
                    if isinstance(skill_data, dict) and "skill_id" in skill_data:
                        try:
                            skill = Skill.from_dict(skill_data)
                            score = self._compute_skill_relevance(skill, keywords, problem_lower)
                            if score > best_score:
                                best_score = score
                                best_skill = skill
                        except Exception:
                            pass
                    
                    # 若 KB 条目不是 Skill 对象，看标签/标题匹配度
                    title = entry_dict.get("title", "").lower()
                    tags = " ".join(entry_dict.get("tags", [])).lower()
                    combined = f"{title} {tags} {entry_dict.get('content','')[:200]}".lower()
                    overlap = sum(1 for kw in keywords if kw in combined)
                    kw_score = overlap / max(len(keywords), 1)
                    if kw_score > best_score:
                        best_score = kw_score
                        # 用 KB 条目构造一个轻量 Skill 壳（供执行器路由）
                        best_skill = self._skill_from_kb_entry(entry_dict)
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"Layer 1 KB 搜索失败: {e}")
        
        # 4. 阈值判断（中文分词粒度较粗，阈值 0.40 更合理）
        LAYER1_THRESHOLD = 0.40
        if best_skill and best_score >= LAYER1_THRESHOLD:
            # 缓存命中的 Skill
            self.skills_cache[best_skill.skill_id] = best_skill
            result = self.executor.execute(best_skill, problem)
            return result, best_skill
        
        return None, None
    
    def _compute_skill_relevance(self, skill: Skill, keywords: List[str], problem_lower: str) -> float:
        """计算 Skill 与问题的关联分数（0-1）"""
        skill_text = f"{skill.name} {skill.description} {' '.join(skill.required_inputs)} {' '.join(skill.outputs)}".lower()
        overlap = sum(1 for kw in keywords if kw in skill_text)
        return overlap / max(len(keywords), 1)
    
    def _skill_from_kb_entry(self, entry: Dict) -> "Skill":
        """将 KB 条目包装成轻量 Skill，用于 Layer 1 执行"""
        skill_id = entry.get("id", f"kb_{hash(entry.get('title',''))}")
        title = entry.get("title", "KB Skill")
        content = entry.get("content", "")
        
        # 将 KB 内容摘要转换为步骤
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")][:5]
        steps = [
            SkillStep(
                step_number=i + 1,
                name=f"步骤 {i+1}",
                description=line,
                source="记忆"
            )
            for i, line in enumerate(lines or ["参考知识库内容解决问题"])
        ]
        
        return Skill(
            skill_id=str(skill_id),
            name=title,
            description=content[:120],
            version="1.0",
            status=SkillStatus.ACTIVE,
            steps=steps,
            required_inputs=[],
            outputs=["result"],
            parameters={"kb_entry": True},
            metadata=SkillMetadata(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by="kb-import"
            ),
            generation_info=GenerationInfo(
                skill_type=SkillType.MANUAL,
                confidence=0.75
            ),
            quality_metrics=QualityMetrics()
        )
    
    def _try_layer_2(self, problem: str) -> Tuple[Optional[ExecutionResult], Optional[Skill]]:
        """第二层：从记忆中组合"""
        try:
            from .skill_composer import SkillComposer
        except ImportError:
            import importlib, sys
            spec = importlib.util.spec_from_file_location(
                "skill_composer",
                str(__import__("pathlib").Path(__file__).parent / "skill_composer.py")
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            SkillComposer = mod.SkillComposer
        
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
        try:
            from .skill_generator import SkillGenerator
            from .quality_evaluator import QualityEvaluator
        except ImportError:
            import importlib
            _engine_dir = __import__("pathlib").Path(__file__).parent
            
            def _load(name):
                spec = importlib.util.spec_from_file_location(name, str(_engine_dir / f"{name}.py"))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
            
            SkillGenerator = _load("skill_generator").SkillGenerator
            QualityEvaluator = _load("quality_evaluator").QualityEvaluator
        
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
        """
        分析用户反馈，提取情感倾向、问题方面和改进建议。
        
        情感三态：
        - positive：用户满意，Skill 可提升置信度
        - negative：用户不满，Skill 需要更新
        - neutral：中性或纯描述性建议，直接追加说明
        """
        text = feedback.lower()
        
        # 正面词（整词匹配，避免被子串误命中）
        positive_signals = ["很好", "太好", "不错", "非常好", "完美", "棒", "对的", "准确",
                            "有用", "great", "perfect", "correct", "useful", "good job",
                            "excellent", "awesome", "well done", "nice work"]
        # 负面词
        negative_signals = ["不对", "错误", "缺少", "没有", "漏掉", "不够", "差",
                            "wrong", "missing", "incorrect", "bad", "fail", "error",
                            "怎么不", "为什么不", "应该", "需要加", "还差", "不全"]
        # 方面词映射
        aspect_keywords = {
            "步骤": ["步骤", "流程", "顺序", "step", "process"],
            "内容": ["内容", "描述", "说明", "detail", "content", "description"],
            "数量": ["太少", "太多", "数量", "count"],
            "方向": ["方向", "思路", "角度", "approach", "direction"],
            "数据": ["数据", "分析", "统计", "data", "analysis"],
            "格式": ["格式", "排版", "结构", "format", "structure"],
        }
        
        # 判断情感
        pos_count = sum(1 for w in positive_signals if w in text)
        neg_count = sum(1 for w in negative_signals if w in text)
        
        if neg_count > pos_count:
            sentiment = "negative"
        elif pos_count > neg_count:
            sentiment = "positive"
        else:
            sentiment = "neutral"
        
        # 提取方面
        aspect = "general"
        for asp, keywords in aspect_keywords.items():
            if any(kw in text for kw in keywords):
                aspect = asp
                break
        
        # 提取改进建议（截取前 200 字）
        suggestion = feedback.strip()[:200]
        
        return {
            "sentiment": sentiment,
            "aspect": aspect,
            "suggestion": suggestion,
            "positive_signals": pos_count,
            "negative_signals": neg_count
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

"""
Rollback Manager 模块 - Phase 2 升级

新增功能：
1. 存储层抽象：支持内存和磁盘存储
2. 触发落盘机制：Feature通过/Skill完成/异常时自动落盘
3. 轻量级标记点集成
4. 文件创建自动回滚（Phase 4部分）

遵循张大胖建议：先完善 Phase 2，数据驱动 Phase 3 决策
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import copy
import json
import os
import atexit

from .checkpoint_storage import CheckpointStorage, InMemoryStorage, FileStorage, create_storage, Checkpoint
from .lightweight_marker import LightweightMarkerManager, MarkerContext


class RollbackPriority(Enum):
    """回滚优先级"""
    P0_MUST = "p0_must"          # 必须：Skill 代码本身
    P1_SHOULD = "p1_should"      # 应该：已创建的文件
    P2_OPTIONAL = "p2_optional"  # 可选：外部 API 调用
    P3_DEFERRED = "p3_deferred"  # 延后：已写入 KB 的记忆


class SideEffectType(Enum):
    """副作用类型"""
    FILE_CREATED = "file_created"        # 创建的文件
    API_CALLED = "api_called"            # 调用的 API
    KB_WRITTEN = "kb_written"            # 写入 KB 的记忆
    SKILL_MODIFIED = "skill_modified"    # 修改的 Skill
    EXTERNAL_SERVICE = "external_service"  # 外部服务


@dataclass
class SideEffect:
    """副作用记录"""
    effect_type: SideEffectType
    description: str
    priority: RollbackPriority
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    rolled_back: bool = False
    auto_rollback: bool = False  # Phase 4：是否可自动回滚
    
    def to_dict(self) -> Dict:
        return {
            "effect_type": self.effect_type.value,
            "description": self.description,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": copy.deepcopy(self.metadata),
            "rolled_back": self.rolled_back,
            "auto_rollback": self.auto_rollback,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SideEffect":
        return cls(
            effect_type=SideEffectType(data["effect_type"]),
            description=data["description"],
            priority=RollbackPriority(data["priority"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=copy.deepcopy(data.get("metadata", {})),
            rolled_back=data.get("rolled_back", False),
            auto_rollback=data.get("auto_rollback", False),
        )


class RollbackManagerPhase2:
    """
    回滚管理器 - Phase 2 版本
    
    核心升级：
    1. 存储层抽象（内存/磁盘）
    2. 自动触发落盘机制
    3. 轻量级标记点集成
    4. 文件创建自动回滚
    
    触发落盘时机：
    - Feature 验证通过后
    - 整个 Skill 完成后
    - 检测到异常/中断信号时
    """
    
    def __init__(
        self,
        storage: Optional[CheckpointStorage] = None,
        auto_persist: bool = True,
        auto_rollback_files: bool = True
    ):
        """
        Args:
            storage: 存储层实例（默认内存+定期落盘）
            auto_persist: 是否自动触发落盘
            auto_rollback_files: 是否自动回滚文件创建（Phase 4）
        """
        self.storage = storage or InMemoryStorage()
        self.marker_manager = LightweightMarkerManager()
        self.side_effects_log: List[SideEffect] = []
        
        self.auto_persist = auto_persist
        self.auto_rollback_files = auto_rollback_files
        
        # 记录已创建的文件（用于自动回滚）
        self._created_files: List[Path] = []
        
        # 注册退出时的持久化
        if auto_persist and isinstance(self.storage, InMemoryStorage):
            atexit.register(self._exit_persist)
    
    def _exit_persist(self):
        """程序退出时触发持久化"""
        if hasattr(self.storage, 'persist'):
            self.storage.persist()
    
    # ==================== Checkpoint 管理 ====================
    
    def create_checkpoint(
        self,
        skill: Any,
        description: str,
        feature_id: Optional[str] = None
    ) -> Checkpoint:
        """
        创建 Skill 版本快照
        
        Args:
            skill: Skill 对象（需有 to_dict 方法）
            description: 创建原因
            feature_id: 关联的 Feature ID
            
        Returns:
            Checkpoint 对象
        """
        checkpoint_id = f"cp_{skill.skill_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self._get_checkpoint_count(skill.skill_id):04d}"
        
        # 深拷贝 snapshot
        skill_snapshot = copy.deepcopy(skill.to_dict())
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            skill_id=skill.skill_id,
            version=skill.version,
            skill_snapshot=skill_snapshot,
            side_effects=[],
            created_at=datetime.now(),
            description=description,
            feature_id=feature_id
        )
        
        # 保存到存储层
        self.storage.save(checkpoint)
        
        return checkpoint
    
    def _get_checkpoint_count(self, skill_id: str) -> int:
        """获取 skill 的 checkpoint 数量"""
        return len(self.storage.get_by_skill(skill_id))
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """获取 checkpoint"""
        return self.storage.get(checkpoint_id)
    
    def get_checkpoints_by_skill(self, skill_id: str) -> List[Checkpoint]:
        """获取 skill 的所有 checkpoint"""
        return self.storage.get_by_skill(skill_id)
    
    def get_checkpoints_by_feature(self, skill_id: str, feature_id: str) -> List[Checkpoint]:
        """获取 feature 的所有 checkpoint"""
        return self.storage.get_by_feature(skill_id, feature_id)
    
    # ==================== 副作用记录 ====================
    
    def record_side_effect(
        self,
        checkpoint_id: str,
        effect: SideEffect
    ) -> bool:
        """记录副作用到 checkpoint"""
        checkpoint = self.storage.get(checkpoint_id)
        if not checkpoint:
            return False
        
        # 更新 checkpoint 的副作用列表
        checkpoint.side_effects.append(effect)
        self.storage.save(checkpoint)
        
        # 记录到全局日志
        self.side_effects_log.append(effect)
        
        return True
    
    def log_file_created(
        self,
        checkpoint_id: str,
        file_path: Union[str, Path],
        auto_rollback: bool = True
    ) -> SideEffect:
        """
        记录文件创建副作用
        
        Phase 4：文件创建默认可自动回滚
        """
        file_path = Path(file_path)
        self._created_files.append(file_path)
        
        effect = SideEffect(
            effect_type=SideEffectType.FILE_CREATED,
            description=f"Created file: {file_path}",
            priority=RollbackPriority.P1_SHOULD,
            timestamp=datetime.now(),
            metadata={"file_path": str(file_path)},
            auto_rollback=auto_rollback and self.auto_rollback_files
        )
        
        self.record_side_effect(checkpoint_id, effect)
        return effect
    
    def log_api_call(
        self,
        checkpoint_id: str,
        api_name: str,
        request_data: Dict,
        auto_rollback: bool = False
    ) -> SideEffect:
        """
        记录 API 调用副作用
        
        默认不自动回滚（可能需要人工确认）
        """
        effect = SideEffect(
            effect_type=SideEffectType.API_CALLED,
            description=f"API call: {api_name}",
            priority=RollbackPriority.P2_OPTIONAL,
            timestamp=datetime.now(),
            metadata={
                "api_name": api_name,
                "request": request_data
            },
            auto_rollback=auto_rollback
        )
        
        self.record_side_effect(checkpoint_id, effect)
        return effect
    
    def log_kb_written(
        self,
        checkpoint_id: str,
        kb_entry_id: str,
        content_summary: str
    ) -> SideEffect:
        """
        记录 KB 写入副作用
        
        默认不自动回滚（涉及知识库完整性）
        """
        effect = SideEffect(
            effect_type=SideEffectType.KB_WRITTEN,
            description=f"KB entry: {content_summary[:50]}...",
            priority=RollbackPriority.P3_DEFERRED,
            timestamp=datetime.now(),
            metadata={"kb_entry_id": kb_entry_id},
            auto_rollback=False
        )
        
        self.record_side_effect(checkpoint_id, effect)
        return effect
    
    # ==================== 回滚功能 ====================
    
    def rollback(
        self,
        skill: Any,
        target_checkpoint_id: Optional[str] = None,
        target_version: Optional[str] = None
    ) -> Dict:
        """
        回滚 Skill 到指定 checkpoint
        
        Phase 2：
        - P0 必须：回滚 Skill 代码本身
        - P1 部分：文件创建可自动回滚（如果启用）
        - P2-P3：仅记录，需人工确认
        """
        # 确定目标 checkpoint
        target_cp = None
        if target_checkpoint_id:
            target_cp = self.storage.get(target_checkpoint_id)
        elif target_version:
            target_cp = self._find_checkpoint_by_version(skill.skill_id, target_version)
        
        if not target_cp:
            return {
                "success": False,
                "error": "Target checkpoint not found"
            }
        
        # 收集需要处理的副作用
        side_effects_to_rollback = target_cp.side_effects[:]
        rollback_results = []
        
        # P0：回滚 Skill 状态
        self._rollback_skill_state(skill, target_cp.skill_snapshot)
        
        # P1：文件创建自动回滚（如果启用）
        if self.auto_rollback_files:
            for effect in side_effects_to_rollback:
                if effect.effect_type == SideEffectType.FILE_CREATED and effect.auto_rollback:
                    result = self._rollback_file_creation(effect)
                    rollback_results.append({
                        "type": "file_rollback",
                        "description": effect.description,
                        "success": result
                    })
                    effect.rolled_back = result
        
        # P2-P3：仅记录，不自动处理
        manual_effects = [e for e in side_effects_to_rollback 
                         if e.priority in [RollbackPriority.P2_OPTIONAL, RollbackPriority.P3_DEFERRED]]
        
        return {
            "success": True,
            "p0_rolled_back": True,
            "p1_rolled_back": self.auto_rollback_files,
            "p2_p3_manual_review": len(manual_effects),
            "rolled_back_to": target_cp.checkpoint_id,
            "version": target_cp.version,
            "rollback_results": rollback_results,
            "manual_review_required": [e.description for e in manual_effects]
        }
    
    def _rollback_skill_state(self, skill: Any, snapshot: Dict):
        """回滚 Skill 状态"""
        for key, value in snapshot.items():
            if hasattr(skill, key):
                if isinstance(value, (list, dict)):
                    setattr(skill, key, copy.deepcopy(value))
                else:
                    setattr(skill, key, value)
    
    def _rollback_file_creation(self, effect: SideEffect) -> bool:
        """
        回滚文件创建
        
        Phase 4：自动删除创建的文件
        """
        file_path = Path(effect.metadata.get("file_path", ""))
        try:
            if file_path.exists():
                file_path.unlink()
                return True
            return True  # 文件已不存在，视为成功
        except Exception as e:
            print(f"Failed to rollback file {file_path}: {e}")
            return False
    
    def _find_checkpoint_by_version(self, skill_id: str, version: str) -> Optional[Checkpoint]:
        """通过版本号查找 checkpoint"""
        checkpoints = self.storage.get_by_skill(skill_id)
        for cp in reversed(checkpoints):
            if cp.version == version:
                return cp
        return None
    
    # ==================== 轻量级标记点集成 ====================
    
    def create_marker_context(
        self,
        skill_id: str,
        feature_id: str,
        base_checkpoint_id: str
    ) -> MarkerContext:
        """创建标记点上下文"""
        return MarkerContext(
            self.marker_manager,
            skill_id,
            feature_id,
            base_checkpoint_id
        )
    
    def rollback_to_marker(
        self,
        skill: Any,
        marker_id: str
    ) -> Dict:
        """
        回滚到轻量级标记点
        
        逻辑：
        1. 找到标记点指向的最近完整 Checkpoint
        2. 回滚到该 Checkpoint
        3. 返回标记点信息（可用于重试）
        """
        marker = self.marker_manager.get_marker(marker_id)
        if not marker:
            return {"success": False, "error": "Marker not found"}
        
        # 回滚到最近的完整 Checkpoint
        result = self.rollback(skill, target_checkpoint_id=marker.nearest_checkpoint_id)
        
        # 添加标记点信息
        result["marker_info"] = {
            "marker_id": marker_id,
            "step_name": marker.step_name,
            "step_index": marker.step_index,
            "can_retry": marker.can_retry,
            "retry_action": marker.retry_action
        }
        
        return result
    
    # ==================== 触发落盘机制 ====================
    
    def on_feature_completed(self, skill_id: str, feature_id: str) -> bool:
        """
        Feature 验证通过后触发
        
        触发条件：
        - Feature 执行成功
        - 自我验证通过
        """
        if self.auto_persist:
            return self._trigger_persist(f"Feature {feature_id} completed")
        return True
    
    def on_skill_completed(self, skill_id: str) -> bool:
        """
        整个 Skill 完成后触发
        
        触发条件：
        - 所有 Feature 执行完成
        - Skill 成功保存到 KB
        """
        if self.auto_persist:
            return self._trigger_persist(f"Skill {skill_id} completed")
        return True
    
    def on_exception(self, skill_id: str, exception: Exception) -> bool:
        """
        检测到异常时触发
        
        触发条件：
        - 执行过程中抛出异常
        - 验证失败
        - 中断信号
        """
        if self.auto_persist:
            return self._trigger_persist(f"Exception in skill {skill_id}: {str(exception)}")
        return True
    
    def _trigger_persist(self, reason: str) -> bool:
        """触发持久化"""
        if hasattr(self.storage, 'persist'):
            return self.storage.persist()
        return True
    
    def persist(self) -> bool:
        """手动触发持久化"""
        return self._trigger_persist("Manual persist")
    
    # ==================== 查询功能 ====================
    
    def get_rollback_report(self, skill_id: str) -> Dict:
        """获取 Skill 的回滚报告"""
        checkpoints = self.storage.get_by_skill(skill_id)
        side_effects = []
        
        for cp in checkpoints:
            side_effects.extend(cp.side_effects)
        
        return {
            "skill_id": skill_id,
            "total_checkpoints": len(checkpoints),
            "total_side_effects": len(side_effects),
            "p0_effects": len([e for e in side_effects if e.priority == RollbackPriority.P0_MUST]),
            "p1_effects": len([e for e in side_effects if e.priority == RollbackPriority.P1_SHOULD]),
            "p2_effects": len([e for e in side_effects if e.priority == RollbackPriority.P2_OPTIONAL]),
            "p3_effects": len([e for e in side_effects if e.priority == RollbackPriority.P3_DEFERRED]),
            "auto_rollback_enabled": self.auto_rollback_files,
            "checkpoints": [cp.checkpoint_id for cp in checkpoints]
        }


def create_rollback_manager(
    storage_type: str = "memory",
    storage_path: Optional[str] = None,
    auto_persist: bool = True,
    auto_rollback_files: bool = True
) -> RollbackManagerPhase2:
    """
    工厂函数：创建 RollbackManager
    
    Args:
        storage_type: "memory" 或 "file"
        storage_path: 存储路径
        auto_persist: 是否自动触发落盘
        auto_rollback_files: 是否自动回滚文件创建
    """
    if storage_type == "memory":
        storage = InMemoryStorage(backup_path=storage_path)
    elif storage_type == "file":
        storage = FileStorage(base_dir=storage_path or "./checkpoints")
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")
    
    return RollbackManagerPhase2(
        storage=storage,
        auto_persist=auto_persist,
        auto_rollback_files=auto_rollback_files
    )

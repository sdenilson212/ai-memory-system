"""
Rollback Manager 模块 - Phase 1 实现

功能：
1. 创建 Skill 版本快照（checkpoint）
2. P0 级回滚：回滚 Skill 代码本身
3. 记录副作用日志（P1-P3级暂不处理，仅记录）

遵循张大胖建议：分层回滚策略，P0必须，P1-P3逐步完善
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import copy
import json
import os


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
    
    def to_dict(self) -> Dict:
        return {
            "effect_type": self.effect_type.value,
            "description": self.description,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "rolled_back": self.rolled_back,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SideEffect":
        return cls(
            effect_type=SideEffectType(data["effect_type"]),
            description=data["description"],
            priority=RollbackPriority(data["priority"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            rolled_back=data.get("rolled_back", False),
        )


@dataclass
class Checkpoint:
    """
    Skill 版本快照
    
    包含：
    - 版本标识
    - Skill 状态快照
    - 产生时的副作用列表
    - 时间戳和元数据
    """
    checkpoint_id: str
    skill_id: str
    version: str
    skill_snapshot: Dict[str, Any]  # Skill 的完整状态
    side_effects: List[SideEffect]  # 创建此版本时产生的副作用
    created_at: datetime
    description: str                # 创建原因
    feature_id: Optional[str] = None  # 关联的 Feature ID
    
    def to_dict(self) -> Dict:
        return {
            "checkpoint_id": self.checkpoint_id,
            "skill_id": self.skill_id,
            "version": self.version,
            "skill_snapshot": self.skill_snapshot,
            "side_effects": [se.to_dict() for se in self.side_effects],
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "feature_id": self.feature_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Checkpoint":
        return cls(
            checkpoint_id=data["checkpoint_id"],
            skill_id=data["skill_id"],
            version=data["version"],
            skill_snapshot=data["skill_snapshot"],
            side_effects=[SideEffect.from_dict(se) for se in data.get("side_effects", [])],
            created_at=datetime.fromisoformat(data["created_at"]),
            description=data["description"],
            feature_id=data.get("feature_id"),
        )


class RollbackManager:
    """
    回滚管理器
    
    核心功能：
    1. 创建 checkpoint（版本快照）
    2. 记录副作用（用于后续清理）
    3. P0 级回滚（Skill 本身）
    
    设计原则：
    - 回滚时至少记录所有副作用，即使不立即清理
    - RollbackManager 维护 side_effects_log，知道有哪些坑要填
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        self.checkpoints: Dict[str, Checkpoint] = {}  # checkpoint_id -> Checkpoint
        self.skill_checkpoints: Dict[str, List[str]] = {}  # skill_id -> [checkpoint_ids]
        self.side_effects_log: List[SideEffect] = []  # 所有副作用的记录
        self.storage_path = storage_path
        
        if storage_path and os.path.exists(storage_path):
            self._load_from_storage()
    
    def create_checkpoint(self, skill: Any, description: str, 
                         feature_id: Optional[str] = None) -> Checkpoint:
        """
        创建 Skill 版本快照
        
        Args:
            skill: Skill 对象（需有 to_dict 方法）
            description: 创建原因
            feature_id: 关联的 Feature ID
            
        Returns:
            Checkpoint 对象
        """
        import copy
        checkpoint_id = f"cp_{skill.skill_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.checkpoints):04d}"
        
        # 深拷贝 snapshot，避免后续修改影响已保存的 checkpoint
        skill_snapshot = copy.deepcopy(skill.to_dict())
        
        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            skill_id=skill.skill_id,
            version=skill.version,
            skill_snapshot=skill_snapshot,
            side_effects=[],  # 初始为空，后续添加
            created_at=datetime.now(),
            description=description,
            feature_id=feature_id
        )
        
        # 保存 checkpoint
        self.checkpoints[checkpoint_id] = checkpoint
        
        # 更新 skill -> checkpoint 映射
        if skill.skill_id not in self.skill_checkpoints:
            self.skill_checkpoints[skill.skill_id] = []
        self.skill_checkpoints[skill.skill_id].append(checkpoint_id)
        
        # 持久化
        if self.storage_path:
            self._save_to_storage()
        
        return checkpoint
    
    def record_side_effect(self, checkpoint_id: str, effect: SideEffect):
        """
        记录副作用到指定 checkpoint
        
        Args:
            checkpoint_id: Checkpoint ID
            effect: 副作用记录
        """
        if checkpoint_id in self.checkpoints:
            self.checkpoints[checkpoint_id].side_effects.append(effect)
            self.side_effects_log.append(effect)
            
            if self.storage_path:
                self._save_to_storage()
    
    def log_side_effect(self, effect_type: SideEffectType, description: str,
                       priority: RollbackPriority, metadata: Dict[str, Any] = None):
        """
        记录副作用（便捷方法，不关联特定 checkpoint）
        
        用于在回滚时知道有哪些副作用需要处理
        """
        effect = SideEffect(
            effect_type=effect_type,
            description=description,
            priority=priority,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.side_effects_log.append(effect)
        
        if self.storage_path:
            self._save_to_storage()
        
        return effect
    
    def rollback(self, skill: Any, target_checkpoint_id: Optional[str] = None,
                target_version: Optional[str] = None) -> Dict:
        """
        回滚 Skill 到指定 checkpoint 或版本
        
        Phase 1 实现：
        - P0 必须：回滚 Skill 代码本身
        - P1-P3：仅记录，不自动清理（后续人工确认）
        
        Args:
            skill: 要回滚的 Skill 对象（会被修改）
            target_checkpoint_id: 目标 Checkpoint ID（优先）
            target_version: 目标版本号（备选）
            
        Returns:
            回滚结果报告
        """
        # 确定目标 checkpoint
        target_cp = None
        if target_checkpoint_id:
            target_cp = self.checkpoints.get(target_checkpoint_id)
        elif target_version:
            target_cp = self._find_checkpoint_by_version(skill.skill_id, target_version)
        
        if not target_cp:
            return {
                "success": False,
                "error": f"找不到目标 checkpoint: {target_checkpoint_id or target_version}",
                "p0_rolled_back": False,
                "pending_side_effects": []
            }
        
        # P0: 回滚 Skill 本身
        try:
            self._rollback_skill_state(skill, target_cp.skill_snapshot)
            p0_success = True
        except Exception as e:
            return {
                "success": False,
                "error": f"P0 回滚失败: {str(e)}",
                "p0_rolled_back": False,
                "pending_side_effects": []
            }
        
        # P1-P3: 记录副作用，但不自动清理
        pending_effects = self._collect_pending_side_effects(target_cp)
        
        # 标记 checkpoint 中的副作用为待处理
        for effect in target_cp.side_effects:
            if effect.priority != RollbackPriority.P0_MUST:
                # 记录到待处理列表，但不自动回滚
                pass
        
        return {
            "success": True,
            "p0_rolled_back": p0_success,
            "rolled_back_to": target_cp.checkpoint_id,
            "version": target_cp.version,
            "pending_side_effects": [
                {
                    "type": e.effect_type.value,
                    "description": e.description,
                    "priority": e.priority.value,
                    "needs_manual_cleanup": e.priority != RollbackPriority.P0_MUST
                }
                for e in pending_effects
            ],
            "warning": f"有 {len(pending_effects)} 个副作用需要人工确认清理"
        }
    
    def _rollback_skill_state(self, skill: Any, snapshot: Dict):
        """回滚 Skill 状态"""
        # 直接设置属性 - 更可靠的回滚方式
        for key, value in snapshot.items():
            if hasattr(skill, key):
                # 对于列表和字典，需要深拷贝避免引用问题
                if isinstance(value, (list, dict)):
                    import copy
                    setattr(skill, key, copy.deepcopy(value))
                else:
                    setattr(skill, key, value)
    
    def _collect_pending_side_effects(self, checkpoint: Checkpoint) -> List[SideEffect]:
        """收集待处理的副作用（P1-P3）"""
        return [e for e in checkpoint.side_effects 
                if e.priority != RollbackPriority.P0_MUST and not e.rolled_back]
    
    def _find_checkpoint_by_version(self, skill_id: str, version: str) -> Optional[Checkpoint]:
        """通过版本号查找 checkpoint"""
        cp_ids = self.skill_checkpoints.get(skill_id, [])
        for cp_id in reversed(cp_ids):  # 从新到旧
            cp = self.checkpoints.get(cp_id)
            if cp and cp.version == version:
                return cp
        return None
    
    def get_checkpoints_for_skill(self, skill_id: str) -> List[Checkpoint]:
        """获取 Skill 的所有 checkpoint"""
        cp_ids = self.skill_checkpoints.get(skill_id, [])
        return [self.checkpoints[cp_id] for cp_id in cp_ids if cp_id in self.checkpoints]
    
    def get_latest_checkpoint(self, skill_id: str) -> Optional[Checkpoint]:
        """获取 Skill 的最新 checkpoint"""
        checkpoints = self.get_checkpoints_for_skill(skill_id)
        return checkpoints[-1] if checkpoints else None
    
    def _save_to_storage(self):
        """持久化到存储"""
        if not self.storage_path:
            return
        
        data = {
            "checkpoints": {k: v.to_dict() for k, v in self.checkpoints.items()},
            "skill_checkpoints": self.skill_checkpoints,
            "side_effects_log": [se.to_dict() for se in self.side_effects_log],
            "saved_at": datetime.now().isoformat()
        }
        
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_from_storage(self):
        """从存储加载"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.checkpoints = {
                k: Checkpoint.from_dict(v) 
                for k, v in data.get("checkpoints", {}).items()
            }
            self.skill_checkpoints = data.get("skill_checkpoints", {})
            self.side_effects_log = [
                SideEffect.from_dict(se) 
                for se in data.get("side_effects_log", [])
            ]
        except Exception as e:
            print(f"加载 rollback 存储失败: {e}")
    
    def get_side_effects_summary(self, skill_id: Optional[str] = None) -> Dict:
        """
        获取副作用汇总报告
        
        用于了解有哪些副作用需要清理
        """
        if skill_id:
            effects = []
            for cp_id in self.skill_checkpoints.get(skill_id, []):
                cp = self.checkpoints.get(cp_id)
                if cp:
                    effects.extend(cp.side_effects)
        else:
            effects = self.side_effects_log
        
        summary = {
            "total": len(effects),
            "by_priority": {},
            "by_type": {},
            "rolled_back": 0,
            "pending": 0
        }
        
        for e in effects:
            # 按优先级统计
            p = e.priority.value
            summary["by_priority"][p] = summary["by_priority"].get(p, 0) + 1
            
            # 按类型统计
            t = e.effect_type.value
            summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
            
            # 回滚状态
            if e.rolled_back:
                summary["rolled_back"] += 1
            else:
                summary["pending"] += 1
        
        return summary


# 便捷函数
def create_rollback_manager(storage_path: Optional[str] = None) -> RollbackManager:
    """创建 RollbackManager 实例"""
    return RollbackManager(storage_path)


if __name__ == "__main__":
    # 简单测试
    from dataclasses import dataclass
    
    @dataclass
    class TestSkill:
        skill_id: str
        version: str
        name: str
        steps: List[str]
        
        def to_dict(self):
            return {
                "skill_id": self.skill_id,
                "version": self.version,
                "name": self.name,
                "steps": self.steps
            }
        
        @classmethod
        def from_dict(cls, data):
            return cls(**data)
    
    # 创建测试 Skill
    skill = TestSkill(
        skill_id="test_skill",
        version="1.0",
        name="测试 Skill",
        steps=["步骤1", "步骤2"]
    )
    
    # 创建 RollbackManager
    rm = create_rollback_manager()
    
    # 创建 checkpoint
    cp = rm.create_checkpoint(skill, "初始版本")
    print(f"创建 checkpoint: {cp.checkpoint_id}")
    
    # 修改 Skill
    skill.version = "1.1"
    skill.steps.append("步骤3")
    
    # 记录副作用
    rm.log_side_effect(
        SideEffectType.FILE_CREATED,
        "创建了配置文件",
        RollbackPriority.P1_SHOULD,
        {"file_path": "/tmp/config.txt"}
    )
    
    # 创建新 checkpoint
    cp2 = rm.create_checkpoint(skill, "添加步骤3")
    print(f"创建 checkpoint: {cp2.checkpoint_id}")
    
    # 回滚
    result = rm.rollback(skill, target_checkpoint_id=cp.checkpoint_id)
    print(f"\n回滚结果: {result}")
    print(f"当前版本: {skill.version}")
    print(f"步骤数: {len(skill.steps)}")

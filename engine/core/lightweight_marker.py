"""
轻量级标记点机制

Phase 2 新增：
- 轻量级标记点：不存完整快照，只记录"可以回滚到此处"的参考信息
- 用于关键步骤前后，提供细粒度回滚参考
- 与完整 Checkpoint 配合使用，减少存储开销
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import copy


class MarkerType(Enum):
    """标记点类型"""
    STEP_START = "step_start"      # 步骤开始
    STEP_END = "step_end"          # 步骤结束
    STATE_CHANGE = "state_change"  # 状态变更点
    DECISION_POINT = "decision"    # 决策点
    EXTERNAL_CALL = "external"     # 外部调用（API/文件操作等）


@dataclass
class LightweightMarker:
    """
    轻量级标记点
    
    设计原则：
    - 不存完整状态，只存关键信息
    - 指向最近的完整 Checkpoint
    - 记录回滚所需的最小信息
    """
    marker_id: str
    skill_id: str
    feature_id: str
    marker_type: MarkerType
    
    # 指向最近的完整 Checkpoint
    nearest_checkpoint_id: str
    
    # 位置信息
    step_name: str
    step_index: int
    
    # 状态变更摘要（可选）
    state_delta: Dict[str, Any] = field(default_factory=dict)
    
    # 可重试信息
    can_retry: bool = True
    retry_action: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "marker_id": self.marker_id,
            "skill_id": self.skill_id,
            "feature_id": self.feature_id,
            "marker_type": self.marker_type.value,
            "nearest_checkpoint_id": self.nearest_checkpoint_id,
            "step_name": self.step_name,
            "step_index": self.step_index,
            "state_delta": copy.deepcopy(self.state_delta),
            "can_retry": self.can_retry,
            "retry_action": self.retry_action,
            "created_at": self.created_at.isoformat()
        }


class LightweightMarkerManager:
    """
    轻量级标记点管理器
    
    与 RollbackManager 配合使用：
    - 标记点记录细粒度回滚参考
    - 回滚时先找标记点，再定位到完整 Checkpoint
    """
    
    def __init__(self):
        self._markers: Dict[str, LightweightMarker] = {}
        self._skill_markers: Dict[str, List[str]] = {}  # skill_id -> marker_ids
        self._feature_markers: Dict[str, List[str]] = {}  # feature_id -> marker_ids
    
    def add_marker(
        self,
        skill_id: str,
        feature_id: str,
        marker_type: MarkerType,
        nearest_checkpoint_id: str,
        step_name: str,
        step_index: int,
        state_delta: Optional[Dict] = None,
        can_retry: bool = True,
        retry_action: Optional[str] = None
    ) -> LightweightMarker:
        """
        添加标记点
        
        Args:
            skill_id: Skill ID
            feature_id: Feature ID
            marker_type: 标记点类型
            nearest_checkpoint_id: 最近的完整 Checkpoint ID
            step_name: 步骤名称
            step_index: 步骤索引
            state_delta: 状态变更摘要
            can_retry: 是否可以从此标记点重试
            retry_action: 重试动作（如重新调用某个函数）
        
        Returns:
            创建的标记点
        """
        marker_id = f"marker_{skill_id}_{feature_id}_{step_index}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:17]}"
        
        marker = LightweightMarker(
            marker_id=marker_id,
            skill_id=skill_id,
            feature_id=feature_id,
            marker_type=marker_type,
            nearest_checkpoint_id=nearest_checkpoint_id,
            step_name=step_name,
            step_index=step_index,
            state_delta=state_delta or {},
            can_retry=can_retry,
            retry_action=retry_action
        )
        
        self._markers[marker_id] = marker
        
        # 更新索引
        if skill_id not in self._skill_markers:
            self._skill_markers[skill_id] = []
        self._skill_markers[skill_id].append(marker_id)
        
        if feature_id not in self._feature_markers:
            self._feature_markers[feature_id] = []
        self._feature_markers[feature_id].append(marker_id)
        
        return marker
    
    def get_marker(self, marker_id: str) -> Optional[LightweightMarker]:
        """获取标记点"""
        return self._markers.get(marker_id)
    
    def get_markers_by_skill(self, skill_id: str) -> List[LightweightMarker]:
        """获取 Skill 的所有标记点（按顺序）"""
        marker_ids = self._skill_markers.get(skill_id, [])
        markers = [self._markers[mid] for mid in marker_ids if mid in self._markers]
        return sorted(markers, key=lambda x: x.created_at)
    
    def get_markers_by_feature(self, feature_id: str) -> List[LightweightMarker]:
        """获取 Feature 的所有标记点"""
        marker_ids = self._feature_markers.get(feature_id, [])
        markers = [self._markers[mid] for mid in marker_ids if mid in self._markers]
        return sorted(markers, key=lambda x: x.created_at)
    
    def get_nearest_checkpoint(self, marker_id: str) -> Optional[str]:
        """获取标记点指向的最近 Checkpoint"""
        marker = self._markers.get(marker_id)
        return marker.nearest_checkpoint_id if marker else None
    
    def find_marker_before_step(self, skill_id: str, step_index: int) -> Optional[LightweightMarker]:
        """
        找到指定步骤之前的最后一个标记点
        
        用于失败时回滚到最近的可恢复点
        """
        markers = self.get_markers_by_skill(skill_id)
        candidates = [m for m in markers if m.step_index < step_index]
        
        if candidates:
            # 返回最近的一个
            return max(candidates, key=lambda x: x.step_index)
        return None
    
    def can_retry_from_marker(self, marker_id: str) -> bool:
        """检查是否可以从标记点重试"""
        marker = self._markers.get(marker_id)
        return marker.can_retry if marker else False
    
    def get_retry_action(self, marker_id: str) -> Optional[str]:
        """获取重试动作"""
        marker = self._markers.get(marker_id)
        return marker.retry_action if marker else None
    
    def clear_markers_for_feature(self, feature_id: str) -> int:
        """清除 Feature 的所有标记点，返回清除数量"""
        marker_ids = self._feature_markers.get(feature_id, [])
        count = 0
        
        for marker_id in marker_ids:
            if marker_id in self._markers:
                marker = self._markers[marker_id]
                del self._markers[marker_id]
                count += 1
                
                # 更新 skill 索引
                if marker.skill_id in self._skill_markers:
                    if marker_id in self._skill_markers[marker.skill_id]:
                        self._skill_markers[marker.skill_id].remove(marker_id)
        
        del self._feature_markers[feature_id]
        return count
    
    def clear_all(self):
        """清除所有标记点"""
        self._markers.clear()
        self._skill_markers.clear()
        self._feature_markers.clear()


class MarkerContext:
    """
    标记点上下文管理器
    
    用于在代码中方便地添加标记点：
    
    with MarkerContext(manager, skill_id, feature_id, cp_id) as ctx:
        ctx.mark_step_start("parse_input", 0)
        result = parse_input()
        ctx.mark_step_end("parse_input", 0, {"result": result})
        
        ctx.mark_state_change("update_config", 1, {"config": new_config})
    """
    
    def __init__(
        self,
        manager: LightweightMarkerManager,
        skill_id: str,
        feature_id: str,
        base_checkpoint_id: str
    ):
        self.manager = manager
        self.skill_id = skill_id
        self.feature_id = feature_id
        self.base_checkpoint_id = base_checkpoint_id
        self._step_counter = 0
    
    def mark_step_start(self, step_name: str, can_retry: bool = True):
        """标记步骤开始"""
        marker = self.manager.add_marker(
            skill_id=self.skill_id,
            feature_id=self.feature_id,
            marker_type=MarkerType.STEP_START,
            nearest_checkpoint_id=self.base_checkpoint_id,
            step_name=step_name,
            step_index=self._step_counter,
            can_retry=can_retry
        )
        return marker
    
    def mark_step_end(self, step_name: str, state_delta: Optional[Dict] = None):
        """标记步骤结束"""
        marker = self.manager.add_marker(
            skill_id=self.skill_id,
            feature_id=self.feature_id,
            marker_type=MarkerType.STEP_END,
            nearest_checkpoint_id=self.base_checkpoint_id,
            step_name=step_name,
            step_index=self._step_counter,
            state_delta=state_delta or {},
            can_retry=True
        )
        self._step_counter += 1
        return marker
    
    def mark_state_change(self, description: str, delta: Dict):
        """标记状态变更"""
        marker = self.manager.add_marker(
            skill_id=self.skill_id,
            feature_id=self.feature_id,
            marker_type=MarkerType.STATE_CHANGE,
            nearest_checkpoint_id=self.base_checkpoint_id,
            step_name=description,
            step_index=self._step_counter,
            state_delta=delta
        )
        return marker
    
    def mark_external_call(self, call_desc: str, can_retry: bool = True):
        """标记外部调用"""
        marker = self.manager.add_marker(
            skill_id=self.skill_id,
            feature_id=self.feature_id,
            marker_type=MarkerType.EXTERNAL_CALL,
            nearest_checkpoint_id=self.base_checkpoint_id,
            step_name=call_desc,
            step_index=self._step_counter,
            can_retry=can_retry,
            retry_action=call_desc if can_retry else None
        )
        return marker
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 退出时不清除标记点，由调用者决定何时清除
        pass


def create_marker_manager() -> LightweightMarkerManager:
    """工厂函数：创建标记点管理器"""
    return LightweightMarkerManager()

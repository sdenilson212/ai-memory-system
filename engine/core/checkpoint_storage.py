"""
Checkpoint Storage Layer
存储层抽象，支持内存和磁盘两种实现

Phase 2 新增：
- 抽象基类 CheckpointStorage
- InMemoryStorage: 内存存储（默认）
- FileStorage: 磁盘存储（JSON格式）
- 存储层可无缝切换，业务逻辑无感知
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
import copy


@dataclass
class Checkpoint:
    """Checkpoint 数据结构"""
    checkpoint_id: str
    skill_id: str
    version: str
    skill_snapshot: Dict[str, Any]
    side_effects: List[Dict[str, Any]]
    created_at: datetime
    description: str
    feature_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """转换为字典（深拷贝）"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "skill_id": self.skill_id,
            "version": self.version,
            "skill_snapshot": copy.deepcopy(self.skill_snapshot),
            "side_effects": copy.deepcopy(self.side_effects),
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "feature_id": self.feature_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Checkpoint":
        """从字典创建"""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            skill_id=data["skill_id"],
            version=data["version"],
            skill_snapshot=copy.deepcopy(data["skill_snapshot"]),
            side_effects=copy.deepcopy(data.get("side_effects", [])),
            created_at=datetime.fromisoformat(data["created_at"]),
            description=data["description"],
            feature_id=data.get("feature_id")
        )


class CheckpointStorage(ABC):
    """
    Checkpoint 存储抽象基类
    
    设计原则：
    1. 接口统一：内存和磁盘实现共享同一接口
    2. 深拷贝保证：所有返回的数据都是深拷贝，避免外部修改影响存储
    3. 事务性：支持批量操作，确保数据一致性
    """
    
    @abstractmethod
    def save(self, checkpoint: Checkpoint) -> bool:
        """保存 checkpoint"""
        pass
    
    @abstractmethod
    def get(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """获取单个 checkpoint"""
        pass
    
    @abstractmethod
    def get_by_skill(self, skill_id: str) -> List[Checkpoint]:
        """获取 skill 的所有 checkpoint（按时间排序）"""
        pass
    
    @abstractmethod
    def get_by_feature(self, skill_id: str, feature_id: str) -> List[Checkpoint]:
        """获取 feature 的所有 checkpoint"""
        pass
    
    @abstractmethod
    def list_all(self) -> List[Checkpoint]:
        """列出所有 checkpoint"""
        pass
    
    @abstractmethod
    def delete(self, checkpoint_id: str) -> bool:
        """删除 checkpoint"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """清空所有 checkpoint"""
        pass
    
    @abstractmethod
    def persist(self) -> bool:
        """
        强制持久化（如果支持）
        
        对于内存存储：触发落盘到磁盘（如果配置了备份）
        对于磁盘存储：确保数据写入文件
        """
        pass


class InMemoryStorage(CheckpointStorage):
    """
    内存存储实现
    
    - 快速读写
    - 默认实现
    - 支持可选的备份落盘
    """
    
    def __init__(self, backup_path: Optional[str] = None):
        """
        Args:
            backup_path: 可选的备份文件路径，设置后会定期/手动落盘
        """
        self._storage: Dict[str, Checkpoint] = {}
        self._skill_index: Dict[str, List[str]] = {}  # skill_id -> checkpoint_ids
        self._backup_path = backup_path
    
    def save(self, checkpoint: Checkpoint) -> bool:
        """保存 checkpoint（深拷贝）"""
        # 深拷贝存储，避免外部修改
        cp_copy = Checkpoint(
            checkpoint_id=checkpoint.checkpoint_id,
            skill_id=checkpoint.skill_id,
            version=checkpoint.version,
            skill_snapshot=copy.deepcopy(checkpoint.skill_snapshot),
            side_effects=copy.deepcopy(checkpoint.side_effects),
            created_at=checkpoint.created_at,
            description=checkpoint.description,
            feature_id=checkpoint.feature_id
        )
        
        self._storage[cp_copy.checkpoint_id] = cp_copy
        
        # 更新索引
        if cp_copy.skill_id not in self._skill_index:
            self._skill_index[cp_copy.skill_id] = []
        if cp_copy.checkpoint_id not in self._skill_index[cp_copy.skill_id]:
            self._skill_index[cp_copy.skill_id].append(cp_copy.checkpoint_id)
        
        return True
    
    def get(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """获取 checkpoint（返回深拷贝）"""
        cp = self._storage.get(checkpoint_id)
        if cp:
            return Checkpoint(
                checkpoint_id=cp.checkpoint_id,
                skill_id=cp.skill_id,
                version=cp.version,
                skill_snapshot=copy.deepcopy(cp.skill_snapshot),
                side_effects=copy.deepcopy(cp.side_effects),
                created_at=cp.created_at,
                description=cp.description,
                feature_id=cp.feature_id
            )
        return None
    
    def get_by_skill(self, skill_id: str) -> List[Checkpoint]:
        """获取 skill 的所有 checkpoint（按时间排序）"""
        ids = self._skill_index.get(skill_id, [])
        checkpoints = [self.get(cid) for cid in ids if self.get(cid)]
        return sorted(checkpoints, key=lambda x: x.created_at)
    
    def get_by_feature(self, skill_id: str, feature_id: str) -> List[Checkpoint]:
        """获取 feature 的所有 checkpoint"""
        skill_cps = self.get_by_skill(skill_id)
        return [cp for cp in skill_cps if cp.feature_id == feature_id]
    
    def list_all(self) -> List[Checkpoint]:
        """列出所有 checkpoint"""
        return sorted(
            [self.get(cid) for cid in self._storage.keys()],
            key=lambda x: x.created_at
        )
    
    def delete(self, checkpoint_id: str) -> bool:
        """删除 checkpoint"""
        if checkpoint_id in self._storage:
            cp = self._storage[checkpoint_id]
            del self._storage[checkpoint_id]
            
            # 更新索引
            if cp.skill_id in self._skill_index:
                if checkpoint_id in self._skill_index[cp.skill_id]:
                    self._skill_index[cp.skill_id].remove(checkpoint_id)
            
            return True
        return False
    
    def clear(self) -> bool:
        """清空所有 checkpoint"""
        self._storage.clear()
        self._skill_index.clear()
        return True
    
    def persist(self) -> bool:
        """
        触发备份落盘（如果配置了 backup_path）
        
        返回是否成功落盘
        """
        if not self._backup_path:
            return False
        
        try:
            data = {
                "checkpoints": [cp.to_dict() for cp in self.list_all()],
                "persisted_at": datetime.now().isoformat()
            }
            
            backup_file = Path(self._backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Persist failed: {e}")
            return False
    
    def load_from_disk(self) -> bool:
        """
        从磁盘加载（如果配置了 backup_path 且文件存在）
        
        用于服务重启后恢复状态
        """
        if not self._backup_path:
            return False
        
        backup_file = Path(self._backup_path)
        if not backup_file.exists():
            return False
        
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for cp_dict in data.get("checkpoints", []):
                cp = Checkpoint.from_dict(cp_dict)
                self.save(cp)
            
            return True
        except Exception as e:
            print(f"Load from disk failed: {e}")
            return False


class FileStorage(CheckpointStorage):
    """
    磁盘存储实现
    
    - JSON 格式，便于调试和人工检查
    - 每个 skill 一个文件，避免单文件过大
    - 适合长期存储和审计
    """
    
    def __init__(self, base_dir: str):
        """
        Args:
            base_dir: 存储目录路径
        """
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存（提升读取性能）
        self._cache: Dict[str, Checkpoint] = {}
        self._cache_dirty: set = set()  # 标记需要写入磁盘的 skill_id
    
    def _get_skill_file(self, skill_id: str) -> Path:
        """获取 skill 的存储文件路径"""
        return self._base_dir / f"{skill_id}_checkpoints.json"
    
    def _load_skill_from_disk(self, skill_id: str) -> List[Checkpoint]:
        """从磁盘加载 skill 的所有 checkpoint"""
        file_path = self._get_skill_file(skill_id)
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return [Checkpoint.from_dict(cp_dict) for cp_dict in data.get("checkpoints", [])]
        except Exception as e:
            print(f"Load skill {skill_id} failed: {e}")
            return []
    
    def _save_skill_to_disk(self, skill_id: str, checkpoints: List[Checkpoint]) -> bool:
        """保存 skill 的所有 checkpoint 到磁盘"""
        file_path = self._get_skill_file(skill_id)
        
        try:
            data = {
                "skill_id": skill_id,
                "checkpoints": [cp.to_dict() for cp in checkpoints],
                "updated_at": datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Save skill {skill_id} failed: {e}")
            return False
    
    def save(self, checkpoint: Checkpoint) -> bool:
        """保存 checkpoint"""
        # 更新缓存
        self._cache[checkpoint.checkpoint_id] = Checkpoint(
            checkpoint_id=checkpoint.checkpoint_id,
            skill_id=checkpoint.skill_id,
            version=checkpoint.version,
            skill_snapshot=copy.deepcopy(checkpoint.skill_snapshot),
            side_effects=copy.deepcopy(checkpoint.side_effects),
            created_at=checkpoint.created_at,
            description=checkpoint.description,
            feature_id=checkpoint.feature_id
        )
        
        # 标记为脏
        self._cache_dirty.add(checkpoint.skill_id)
        
        # 立即写入磁盘
        return self._flush_skill(checkpoint.skill_id)
    
    def _flush_skill(self, skill_id: str) -> bool:
        """将 skill 的 checkpoint 写入磁盘"""
        # 获取该 skill 的所有 checkpoint
        skill_cps = self.get_by_skill(skill_id)
        
        # 写入磁盘
        success = self._save_skill_to_disk(skill_id, skill_cps)
        
        if success:
            self._cache_dirty.discard(skill_id)
        
        return success
    
    def get(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """获取 checkpoint"""
        # 先查缓存
        if checkpoint_id in self._cache:
            cp = self._cache[checkpoint_id]
            return Checkpoint(
                checkpoint_id=cp.checkpoint_id,
                skill_id=cp.skill_id,
                version=cp.version,
                skill_snapshot=copy.deepcopy(cp.skill_snapshot),
                side_effects=copy.deepcopy(cp.side_effects),
                created_at=cp.created_at,
                description=cp.description,
                feature_id=cp.feature_id
            )
        
        # 缓存未命中，从磁盘加载所有 skill 的 checkpoint（低效率，实际应该优化）
        for skill_file in self._base_dir.glob("*_checkpoints.json"):
            skill_id = skill_file.stem.replace("_checkpoints", "")
            cps = self._load_skill_from_disk(skill_id)
            for cp in cps:
                self._cache[cp.checkpoint_id] = cp
                if cp.checkpoint_id == checkpoint_id:
                    return Checkpoint(
                        checkpoint_id=cp.checkpoint_id,
                        skill_id=cp.skill_id,
                        version=cp.version,
                        skill_snapshot=copy.deepcopy(cp.skill_snapshot),
                        side_effects=copy.deepcopy(cp.side_effects),
                        created_at=cp.created_at,
                        description=cp.description,
                        feature_id=cp.feature_id
                    )
        
        return None
    
    def get_by_skill(self, skill_id: str) -> List[Checkpoint]:
        """获取 skill 的所有 checkpoint"""
        # 从磁盘加载
        cps = self._load_skill_from_disk(skill_id)
        
        # 更新缓存
        for cp in cps:
            self._cache[cp.checkpoint_id] = cp
        
        return sorted(cps, key=lambda x: x.created_at)
    
    def get_by_feature(self, skill_id: str, feature_id: str) -> List[Checkpoint]:
        """获取 feature 的所有 checkpoint"""
        skill_cps = self.get_by_skill(skill_id)
        return [cp for cp in skill_cps if cp.feature_id == feature_id]
    
    def list_all(self) -> List[Checkpoint]:
        """列出所有 checkpoint"""
        all_cps = []
        for skill_file in self._base_dir.glob("*_checkpoints.json"):
            skill_id = skill_file.stem.replace("_checkpoints", "")
            all_cps.extend(self.get_by_skill(skill_id))
        return sorted(all_cps, key=lambda x: x.created_at)
    
    def delete(self, checkpoint_id: str) -> bool:
        """删除 checkpoint"""
        if checkpoint_id not in self._cache:
            return False
        
        skill_id = self._cache[checkpoint_id].skill_id
        del self._cache[checkpoint_id]
        
        # 重新写入该 skill 的所有 checkpoint
        return self._flush_skill(skill_id)
    
    def clear(self) -> bool:
        """清空所有 checkpoint"""
        self._cache.clear()
        self._cache_dirty.clear()
        
        # 删除所有文件
        for skill_file in self._base_dir.glob("*_checkpoints.json"):
            skill_file.unlink()
        
        return True
    
    def persist(self) -> bool:
        """强制持久化（所有脏数据写入磁盘）"""
        success = True
        for skill_id in list(self._cache_dirty):
            if not self._flush_skill(skill_id):
                success = False
        return success


def create_storage(storage_type: str = "memory", **kwargs) -> CheckpointStorage:
    """
    工厂函数：创建存储实例
    
    Args:
        storage_type: "memory" 或 "file"
        **kwargs: 传递给具体实现的参数
    
    Returns:
        CheckpointStorage 实例
    """
    if storage_type == "memory":
        return InMemoryStorage(**kwargs)
    elif storage_type == "file":
        return FileStorage(**kwargs)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")

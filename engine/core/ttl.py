"""
core/ttl.py — TTL (Time To Live) Manager
记忆生存时间管理器

职责 (Responsibility):
    - 为记忆条目设置过期时间
    - 定期清理过期条目
    - 支持归档而非直接删除
    - 自动 TTL 建议（基于内容类型）

暴露接口 (Exposes):
    TTLManager.set_ttl(entry_id, ttl_days)
    TTLManager.get_ttl(entry_id) -> Optional[int]
    TTLManager.archive_expired() -> list[ArchivedEntry]
    TTLManager.cleanup_expired(delete: bool = False) -> int
    TTLManager.suggest_ttl(content, category) -> int
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class TTLEntry:
    """TTL 记录条目"""
    entry_id: str
    created_at: float           # Unix timestamp
    expires_at: float           # Unix timestamp
    ttl_days: int
    archived: bool = False
    archived_at: Optional[float] = None


@dataclass
class ArchivedEntry:
    """已归档条目"""
    entry_id: str
    original_path: Path
    archive_path: Path
    archived_at: float


class TTLManager:
    """
    管理记忆条目的生存时间。
    
    Usage:
        ttl = TTLManager(memory_dir)
        
        # 设置 30 天 TTL
        ttl.set_ttl("entry-123", 30)
        
        # 自动建议 TTL（基于内容类型）
        suggested = ttl.suggest_ttl("用户喜欢猫的讨论", "preference")
        # → 90（偏好类长期有效）
        
        # 归档过期条目
        archived = ttl.archive_expired()
        
        # 清理过期条目（彻底删除）
        deleted_count = ttl.cleanup_expired(delete=True)
    """

    # 默认 TTL 建议（天数）
    _DEFAULT_TTLS: dict[str, int] = {
        "credential": 365 * 2,    # 凭证类：2年（长期有效）
        "preference": 365,         # 偏好类：1年
        "project": 180,            # 项目类：6个月
        "decision": 90,            # 决策类：3个月
        "goal": 365,               # 目标类：1年
        "conversation": 30,        # 会话摘要：30天
        "technical": 365,          # 技术类：1年
        "event": 30,               # 事件类：30天
    }

    def __init__(self, memory_dir: Path) -> None:
        """
        Args:
            memory_dir: 记忆存储根目录
        """
        self._memory_dir = Path(memory_dir)
        self._ttl_file = self._memory_dir / ".ttl_index.json"
        self._archive_dir = self._memory_dir / ".archive"
        self._archive_dir.mkdir(exist_ok=True)
        
        self._ttl_index: dict[str, dict] = {}
        self._load_index()

    # ── Public Interface ──────────────────────────────────────────────────────

    def set_ttl(self, entry_id: str, ttl_days: int) -> None:
        """
        为条目设置 TTL。
        
        Args:
            entry_id: 条目 ID
            ttl_days: 生存天数（0 表示永不过期）
        """
        now = time.time()
        expires_at = now + (ttl_days * 86400) if ttl_days > 0 else 0
        
        self._ttl_index[entry_id] = {
            "entry_id": entry_id,
            "created_at": now,
            "expires_at": expires_at,
            "ttl_days": ttl_days,
            "archived": False,
            "archived_at": None,
        }
        self._save_index()

    def get_ttl(self, entry_id: str) -> Optional[int]:
        """
        获取条目的 TTL 设置。
        
        Returns:
            TTL 天数，如果未设置则返回 None
        """
        entry = self._ttl_index.get(entry_id)
        if entry:
            return entry.get("ttl_days")
        return None

    def get_expiry(self, entry_id: str) -> Optional[datetime]:
        """
        获取条目的过期时间。
        
        Returns:
            过期时间（datetime），如果永不过期则返回 None
        """
        entry = self._ttl_index.get(entry_id)
        if entry and entry.get("expires_at", 0) > 0:
            return datetime.fromtimestamp(entry["expires_at"])
        return None

    def is_expired(self, entry_id: str) -> bool:
        """
        检查条目是否已过期。
        """
        entry = self._ttl_index.get(entry_id)
        if not entry:
            return False
        
        expires_at = entry.get("expires_at", 0)
        if expires_at == 0:
            return False  # 永不过期
        
        return time.time() > expires_at

    def suggest_ttl(self, content: str, category: str) -> int:
        """
        根据内容类型建议 TTL。
        
        Args:
            content: 条目内容
            category: 条目分类
        
        Returns:
            建议的 TTL 天数
        """
        # 基于分类的建议
        base_ttl = self._DEFAULT_TTLS.get(category, 90)
        
        # 内容长度调整（长内容可能更有价值）
        content_length = len(content)
        if content_length > 1000:
            base_ttl = int(base_ttl * 1.2)  # 长内容 +20%
        elif content_length < 50:
            base_ttl = int(base_ttl * 0.8)   # 短内容 -20%
        
        # 关键词检测（某些关键词暗示长期价值）
        long_term_keywords = [
            "重要", "critical", "必须", "essential", "核心", "core",
            "长期", "long-term", "永久", "permanent", "架构", "architecture"
        ]
        if any(kw in content.lower() for kw in long_term_keywords):
            base_ttl = int(base_ttl * 1.5)  # +50%
        
        return min(base_ttl, 365 * 5)  # 最大 5 年

    def archive_expired(self) -> list[ArchivedEntry]:
        """
        将过期条目归档。
        
        Returns:
            已归档条目列表
        """
        archived: list[ArchivedEntry] = []
        now = time.time()
        
        for entry_id, entry in list(self._ttl_index.items()):
            expires_at = entry.get("expires_at", 0)
            if expires_at > 0 and now > expires_at and not entry.get("archived", False):
                # 查找原始文件
                original_path = self._find_entry_file(entry_id)
                if original_path and original_path.exists():
                    # 归档
                    archive_path = self._archive_dir / f"{entry_id}_{int(now)}.json"
                    shutil.copy2(original_path, archive_path)
                    
                    # 更新索引
                    self._ttl_index[entry_id]["archived"] = True
                    self._ttl_index[entry_id]["archived_at"] = now
                    
                    archived.append(ArchivedEntry(
                        entry_id=entry_id,
                        original_path=original_path,
                        archive_path=archive_path,
                        archived_at=now
                    ))
        
        if archived:
            self._save_index()
        
        return archived

    def cleanup_expired(self, delete: bool = False) -> int:
        """
        清理过期条目。
        
        Args:
            delete: True 则彻底删除，False 则仅归档
        
        Returns:
            处理的条目数量
        """
        if not delete:
            # 仅归档模式
            archived = self.archive_expired()
            return len(archived)
        
        # 彻底删除模式
        deleted = 0
        now = time.time()
        
        for entry_id, entry in list(self._ttl_index.items()):
            expires_at = entry.get("expires_at", 0)
            if expires_at > 0 and now > expires_at:
                # 删除原始文件
                original_path = self._find_entry_file(entry_id)
                if original_path and original_path.exists():
                    original_path.unlink()
                
                # 从索引移除
                del self._ttl_index[entry_id]
                deleted += 1
        
        if deleted:
            self._save_index()
        
        return deleted

    def get_stats(self) -> dict:
        """
        获取 TTL 统计信息。
        
        Returns:
            {
                "total": 总条目数,
                "active": 未过期条目数,
                "expired": 已过期条目数,
                "archived": 已归档条目数,
                "expiring_7d": 7天内过期条目数,
            }
        """
        now = time.time()
        total = len(self._ttl_index)
        expired = sum(1 for e in self._ttl_index.values() if e.get("expires_at", 0) > 0 and e["expires_at"] < now)
        archived = sum(1 for e in self._ttl_index.values() if e.get("archived", False))
        active = total - expired
        expiring_7d = sum(1 for e in self._ttl_index.values() if 0 < e.get("expires_at", 0) - now < 7 * 86400)
        
        return {
            "total": total,
            "active": active,
            "expired": expired,
            "archived": archived,
            "expiring_7d": expiring_7d,
        }

    def extend_ttl(self, entry_id: str, additional_days: int) -> None:
        """
        延长条目的 TTL。
        
        Args:
            entry_id: 条目 ID
            additional_days: 额外天数
        """
        entry = self._ttl_index.get(entry_id)
        if entry:
            current_expires = entry.get("expires_at", time.time())
            new_expires = current_expires + (additional_days * 86400)
            entry["expires_at"] = new_expires
            entry["ttl_days"] = entry.get("ttl_days", 0) + additional_days
            entry["archived"] = False  # 取消归档状态
            self._save_index()

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _load_index(self) -> None:
        """加载 TTL 索引"""
        if self._ttl_file.exists():
            try:
                with open(self._ttl_file, "r", encoding="utf-8") as f:
                    self._ttl_index = json.load(f)
            except Exception:
                self._ttl_index = {}

    def _save_index(self) -> None:
        """保存 TTL 索引"""
        try:
            with open(self._ttl_file, "w", encoding="utf-8") as f:
                json.dump(self._ttl_index, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _find_entry_file(self, entry_id: str) -> Optional[Path]:
        """查找条目文件路径"""
        # 在 ltm 目录中查找
        ltm_dir = self._memory_dir / "ltm"
        for category_dir in ltm_dir.iterdir() if ltm_dir.exists() else []:
            if category_dir.is_dir():
                entry_file = category_dir / f"{entry_id}.md"
                if entry_file.exists():
                    return entry_file
        return None

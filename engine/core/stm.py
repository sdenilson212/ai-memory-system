"""
core/stm.py — Short-Term Memory (Session Tracker)
短期记忆 / 会话追踪器

职责 (Responsibility):
    管理单次对话会话的内存状态，会话结束后自动清除。纯内存操作，无文件 I/O。

暴露接口 (Exposes):
    STMManager.start_session(task_type)           -> STMSession
    STMManager.get_session(session_id)            -> STMSession | None
    STMManager.update_context(session_id, k, v)   -> bool
    STMManager.add_event(session_id, type, text)  -> bool
    STMManager.queue_save(session_id, item)       -> bool
    STMManager.get_pending_saves(session_id)      -> list[dict]
    STMManager.end_session(session_id)            -> dict

依赖 (Depends on):
    纯内存操作，无外部依赖

禁止 (Must NOT):
    - 直接写文件（文件操作由 LTM/KB 负责）
    - 依赖 ltm.py、kb.py、security/
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Data Types
# ─────────────────────────────────────────────────────────────────────────────

VALID_TASK_TYPES = {
    "conversation", "coding", "project", "research",
    "writing", "analysis", "general"
}


@dataclass
class SessionEvent:
    """会话中发生的单个事件 / A single event during a session."""
    timestamp: str
    event_type: str     # memory_trigger | intent_detected | user_correction | milestone
    content: str


@dataclass
class STMSession:
    """单次会话的完整状态 / Complete state of a single session."""
    session_id: str
    started_at: str
    task_type: str
    context: dict[str, Any]         = field(default_factory=dict)
    events: list[SessionEvent]      = field(default_factory=list)
    pending_saves: list[dict]       = field(default_factory=list)
    ended_at: Optional[str]         = None
    is_active: bool                 = True


class STMError(Exception):
    """Base exception for STM operations."""
    pass


# ─────────────────────────────────────────────────────────────────────────────
# STMManager
# ─────────────────────────────────────────────────────────────────────────────

class STMManager:
    """
    In-memory session tracker. All data is cleared when end_session() is called
    or when the process restarts.
    纯内存的会话追踪器。调用 end_session() 或进程重启后数据自动清除。

    Usage / 使用示例:
        stm = STMManager()

        session = stm.start_session(task_type="coding")
        sid = session.session_id

        stm.update_context(sid, "current_project", "memory-engine")
        stm.add_event(sid, "memory_trigger", "User mentioned their name")
        stm.queue_save(sid, {
            "content": "User's name is Denilson",
            "category": "profile",
            "source": "ai-detected",
        })

        summary = stm.end_session(sid)
        # session data is now cleared from memory
    """

    def __init__(self) -> None:
        # session_id -> STMSession
        self._sessions: dict[str, STMSession] = {}

    # ── Public Interface ──────────────────────────────────────────────────────

    def start_session(self, task_type: str = "conversation") -> STMSession:
        """
        Create and register a new session.
        创建并注册一个新的会话。

        Args:
            task_type: 会话类型（conversation/coding/project/research/writing/analysis/general）。

        Returns:
            新创建的 STMSession。
        """
        if task_type not in VALID_TASK_TYPES:
            task_type = "general"

        session = STMSession(
            session_id=str(uuid.uuid4()),
            started_at=_now_iso(),
            task_type=task_type,
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[STMSession]:
        """
        Retrieve a session by ID.
        按 ID 获取会话。

        Args:
            session_id: start_session() 返回的 session_id。

        Returns:
            STMSession 或 None（如果不存在）。
        """
        return self._sessions.get(session_id)

    def update_context(
        self,
        session_id: str,
        key: str,
        value: Any,
    ) -> bool:
        """
        Update or add a key-value pair in the session's context dict.
        在会话上下文中更新或添加键值对。

        Args:
            session_id: 目标会话 ID。
            key:        上下文键名，如 "current_project"、"user_intent"。
            value:      对应的值（任意可序列化类型）。

        Returns:
            True 如果更新成功，False 如果会话不存在或已结束。
        """
        session = self._get_active_session(session_id)
        if session is None:
            return False

        session.context[key] = value
        return True

    def add_event(
        self,
        session_id: str,
        event_type: str,
        content: str,
    ) -> bool:
        """
        Log an event to the session's event timeline.
        向会话的事件时间线记录一个事件。

        Args:
            session_id:  目标会话 ID。
            event_type:  事件类型（memory_trigger/intent_detected/user_correction/milestone）。
            content:     事件内容描述。

        Returns:
            True 如果记录成功，False 如果会话不存在或已结束。
        """
        session = self._get_active_session(session_id)
        if session is None:
            return False

        event = SessionEvent(
            timestamp=_now_iso(),
            event_type=event_type,
            content=content,
        )
        session.events.append(event)
        return True

    def queue_save(self, session_id: str, item: dict) -> bool:
        """
        Add an item to the pending_saves queue for user confirmation.
        将待保存条目加入 pending_saves 队列，等待用户确认。

        item 应包含 / item should contain:
          - content (str): 要保存的内容
          - category (str): 分类
          - source (str): 来源
          - destination (str, optional): "ltm" | "kb"，默认 "ltm"

        Args:
            session_id: 目标会话 ID。
            item:       待保存的条目 dict。

        Returns:
            True 如果加入成功，False 如果会话不存在或已结束。
        """
        session = self._get_active_session(session_id)
        if session is None:
            return False

        if "content" not in item:
            return False

        item.setdefault("destination", "ltm")
        item.setdefault("queued_at", _now_iso())
        session.pending_saves.append(item)
        return True

    def get_pending_saves(self, session_id: str) -> list[dict]:
        """
        Get all items queued for saving.
        获取所有待保存的条目。

        Args:
            session_id: 目标会话 ID。

        Returns:
            pending_saves 列表的副本，如果会话不存在则返回空列表。
        """
        session = self._sessions.get(session_id)
        if session is None:
            return []
        return list(session.pending_saves)

    def end_session(self, session_id: str) -> dict:
        """
        End a session, build a summary, and remove it from memory.
        结束会话，生成摘要，并从内存中清除。

        Args:
            session_id: 要结束的会话 ID。

        Returns:
            session_summary dict 包含：
              - session_id, task_type, started_at, ended_at
              - duration_seconds
              - event_count
              - pending_saves（调用方应处理这些待保存条目）
              - context_snapshot（会话结束时的上下文快照）

        Raises:
            STMError: 如果 session_id 不存在。
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise STMError(f"Session '{session_id}' not found.")

        ended_at = _now_iso()
        session.ended_at = ended_at
        session.is_active = False

        # 计算会话时长
        try:
            start_dt = datetime.fromisoformat(session.started_at)
            end_dt   = datetime.fromisoformat(ended_at)
            duration = int((end_dt - start_dt).total_seconds())
        except Exception:
            duration = -1

        summary = {
            "session_id":       session.session_id,
            "task_type":        session.task_type,
            "started_at":       session.started_at,
            "ended_at":         ended_at,
            "duration_seconds": duration,
            "event_count":      len(session.events),
            "pending_saves":    list(session.pending_saves),
            "context_snapshot": dict(session.context),
            "events":           [asdict(e) for e in session.events],
        }

        # 清除内存 — STM 的数据不持久
        del self._sessions[session_id]

        return summary

    def list_active_sessions(self) -> list[dict]:
        """
        Return a list of all currently active sessions.
        返回所有活跃会话的摘要列表。

        Returns:
            List of dicts: session_id, task_type, started_at, event_count, pending_count
        """
        return [
            {
                "session_id":    s.session_id,
                "task_type":     s.task_type,
                "started_at":    s.started_at,
                "event_count":   len(s.events),
                "pending_count": len(s.pending_saves),
            }
            for s in self._sessions.values()
            if s.is_active
        ]

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _get_active_session(self, session_id: str) -> Optional[STMSession]:
        """Return session only if it exists and is active."""
        session = self._sessions.get(session_id)
        if session is None or not session.is_active:
            return None
        return session


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

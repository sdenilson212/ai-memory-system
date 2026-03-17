"""api/routes/session.py — STM Session Routes"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.stm import STMManager, STMError
from core.ltm import LTMManager
from core.kb import KBManager
from core.trigger import TriggerEngine
from api.server import get_stm, get_ltm, get_kb

_trigger = TriggerEngine()

router = APIRouter()

class StartSessionRequest(BaseModel):
    task_type: str = "conversation"

class UpdateContextRequest(BaseModel):
    key: str
    value: object

class AddEventRequest(BaseModel):
    event_type: str
    content: str

class QueueSaveRequest(BaseModel):
    content: str
    category: str = "other"
    source: str = "ai-detected"
    destination: str = "ltm"

class EndSessionRequest(BaseModel):
    auto_flush: bool = False
    """
    If true, automatically write all pending_saves to LTM or KB before ending.
    如果为 true，结束会话前自动将 pending_saves 写入 LTM 或 KB。
    """

@router.post("/start")
async def start_session(req: StartSessionRequest, stm: STMManager = Depends(get_stm)):
    session = stm.start_session(task_type=req.task_type)
    return {"session_id": session.session_id, "started_at": session.started_at,
            "task_type": session.task_type}

@router.get("/{session_id}/status")
async def session_status(session_id: str, stm: STMManager = Depends(get_stm)):
    session = stm.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return {"session_id": session.session_id, "task_type": session.task_type,
            "started_at": session.started_at, "is_active": session.is_active,
            "event_count": len(session.events),
            "pending_saves_count": len(session.pending_saves),
            "context": session.context}

@router.post("/{session_id}/context")
async def update_context(session_id: str, req: UpdateContextRequest,
                         stm: STMManager = Depends(get_stm)):
    ok = stm.update_context(session_id, req.key, req.value)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or inactive.")
    return {"success": ok, "session_id": session_id, "key": req.key}

@router.post("/{session_id}/event")
async def add_event(session_id: str, req: AddEventRequest,
                    stm: STMManager = Depends(get_stm)):
    ok = stm.add_event(session_id, req.event_type, req.content)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or inactive.")
    return {"success": ok, "session_id": session_id}

@router.post("/{session_id}/queue")
async def queue_save(session_id: str, req: QueueSaveRequest,
                     stm: STMManager = Depends(get_stm)):
    item = {"content": req.content, "category": req.category,
            "source": req.source, "destination": req.destination}
    ok = stm.queue_save(session_id, item)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found or inactive.")
    return {"success": ok, "session_id": session_id, "queued_item": item}

@router.get("/{session_id}/pending")
async def get_pending(session_id: str, stm: STMManager = Depends(get_stm)):
    pending = stm.get_pending_saves(session_id)
    return {"session_id": session_id, "pending_count": len(pending), "items": pending}

@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    req: EndSessionRequest,
    stm: STMManager = Depends(get_stm),
    ltm: LTMManager = Depends(get_ltm),
    kb: KBManager = Depends(get_kb),
):
    """
    End a session. If auto_flush=true, pending_saves are automatically written
    to LTM or KB (based on each item's 'destination' field) before session ends.
    """
    try:
        summary = stm.end_session(session_id)
    except STMError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    flushed: list[dict] = []
    flush_errors: list[dict] = []

    if req.auto_flush and summary.get("pending_saves"):
        for item in summary["pending_saves"]:
            dest = item.get("destination", "ltm")
            try:
                if dest == "kb":
                    entry = kb.add(
                        title=item.get("content", "")[:60],
                        content=item["content"],
                        category=item.get("category", "personal"),
                        source=item.get("source", "ai-detected"),
                    )
                    flushed.append({"destination": "kb", "entry_id": entry.id})
                else:
                    entry = ltm.save(
                        content=item["content"],
                        category=item.get("category", "other"),
                        source=item.get("source", "ai-detected"),
                    )
                    flushed.append({"destination": "ltm", "entry_id": entry.id})
            except Exception as exc:
                flush_errors.append({"content_preview": item.get("content", "")[:40], "error": str(exc)})

    return {
        "success": True,
        "summary": summary,
        "auto_flush": req.auto_flush,
        "flushed_count": len(flushed),
        "flushed": flushed,
        "flush_errors": flush_errors,
    }

@router.get("/active/list")
async def list_active(stm: STMManager = Depends(get_stm)):
    return {"sessions": stm.list_active_sessions()}


@router.get("/{session_id}/suggestions")
async def get_suggestions(session_id: str, stm: STMManager = Depends(get_stm)):
    """
    Analyze session events and return save suggestions (non-destructive).
    分析会话事件，返回建议保存的记忆列表（不自动写入）。
    """
    session = stm.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    events = [
        {"event_type": e.event_type, "content": e.content, "timestamp": e.timestamp}
        for e in session.events
    ]
    suggestions = _trigger.analyze(events)
    return {
        "session_id": session_id,
        "suggestion_count": len(suggestions),
        "suggestions": [
            {
                "content": s.content,
                "destination": s.destination,
                "category": s.category,
                "confidence": round(s.confidence, 2),
                "reason": s.reason,
                "tags": s.tags,
                "source": s.source,
            }
            for s in suggestions
        ],
    }


class AnalyzeTextRequest(BaseModel):
    text: str


@router.post("/analyze")
async def analyze_text(req: AnalyzeTextRequest):
    """
    Analyze arbitrary text for memory save suggestions (no session needed).
    直接分析文本，返回建议保存列表（不需要活跃会话）。
    """
    suggestions = _trigger.analyze_text(req.text)
    return {
        "suggestion_count": len(suggestions),
        "suggestions": [
            {
                "content": s.content,
                "destination": s.destination,
                "category": s.category,
                "confidence": round(s.confidence, 2),
                "reason": s.reason,
                "tags": s.tags,
            }
            for s in suggestions
        ],
    }

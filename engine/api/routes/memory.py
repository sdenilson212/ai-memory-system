"""api/routes/memory.py — LTM Routes"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.ltm import LTMManager, LTMError
from api.server import get_ltm

router = APIRouter()

class SaveRequest(BaseModel):
    content: str = Field(..., min_length=1)
    category: str = "other"
    source: str = "user-explicit"
    tags: list[str] = []
    sensitive: Optional[bool] = None
    passphrase: Optional[str] = None

class UpdateRequest(BaseModel):
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    category: Optional[str] = None

class DeleteRequest(BaseModel):
    confirm: bool = Field(
        False,
        description="Must be true to execute deletion. Safety guard against accidental calls."
    )

@router.post("/save")
async def save_memory(req: SaveRequest, ltm: LTMManager = Depends(get_ltm)):
    entry = ltm.save(
        content=req.content, category=req.category, source=req.source,
        tags=req.tags, sensitive=req.sensitive, passphrase=req.passphrase,
    )
    return {"success": True, "entry_id": entry.id, "sensitive": entry.sensitive,
            "encrypted": entry.encrypted_ref is not None}

@router.get("/recall")
async def recall_memory(
    query: str = Query(...), layer: str = Query("all"),
    category: Optional[str] = Query(None), max_results: int = Query(10),
    ltm: LTMManager = Depends(get_ltm),
):
    results = ltm.search(query=query, category=category, max_results=max_results)
    return {"query": query, "count": len(results),
            "results": [{"id": e.id, "content": e.content, "category": e.category,
                         "tags": e.tags, "source": e.source,
                         "sensitive": e.sensitive, "created_at": e.created_at}
                        for e in results]}

@router.get("/profile")
async def get_profile(ltm: LTMManager = Depends(get_ltm)):
    return ltm.load_profile()

@router.get("/list")
async def list_memories(
    category: Optional[str] = Query(None), limit: int = Query(50),
    ltm: LTMManager = Depends(get_ltm),
):
    entries = ltm.list_all(category=category, limit=limit)
    return {"count": len(entries),
            "entries": [{"id": e.id, "content": e.content, "category": e.category,
                         "tags": e.tags, "created_at": e.created_at} for e in entries]}

@router.get("/{entry_id}")
async def get_memory(entry_id: str, ltm: LTMManager = Depends(get_ltm)):
    entry = ltm.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry '{entry_id}' not found.")
    return {"id": entry.id, "content": entry.content, "category": entry.category,
            "tags": entry.tags, "source": entry.source, "sensitive": entry.sensitive,
            "created_at": entry.created_at, "updated_at": entry.updated_at}

@router.put("/{entry_id}")
async def update_memory(entry_id: str, req: UpdateRequest,
                        ltm: LTMManager = Depends(get_ltm)):
    try:
        entry = ltm.update(entry_id, content=req.content, tags=req.tags, category=req.category)
    except LTMError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"success": True, "entry_id": entry.id, "updated_at": entry.updated_at}

@router.delete("/{entry_id}")
async def delete_memory(
    entry_id: str,
    req: DeleteRequest,
    ltm: LTMManager = Depends(get_ltm),
):
    """Delete a memory entry. Body must include {"confirm": true} to execute."""
    if not req.confirm:
        raise HTTPException(
            status_code=400,
            detail="confirm must be true to execute deletion. This is a safety guard."
        )
    deleted = ltm.delete(entry_id, confirm=True)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Entry '{entry_id}' not found.")
    return {"success": True, "entry_id": entry_id}

"""api/routes/kb.py — Knowledge Base Routes"""
from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.kb import KBManager, KBError
from api.server import get_kb

router = APIRouter()

class AddKBRequest(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    category: str = "personal"
    tags: list[str] = []
    source: str = "user-upload"
    confidence: str = "high"
    confirmed: bool = True

class ImportTextRequest(BaseModel):
    text: str = Field(..., min_length=10)
    category: str = "personal"
    source: str = "user-upload"
    title_prefix: str = "Imported"

class UpdateKBRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    confirmed: Optional[bool] = None

class DeleteKBRequest(BaseModel):
    confirm: bool = Field(
        False,
        description="Must be true to execute deletion. Safety guard."
    )

@router.post("/add")
async def add_kb(req: AddKBRequest, kb: KBManager = Depends(get_kb)):
    entry = kb.add(title=req.title, content=req.content, category=req.category,
                   tags=req.tags, source=req.source, confidence=req.confidence,
                   confirmed=req.confirmed)
    return {"success": True, "entry_id": entry.id, "title": entry.title}

@router.post("/import")
async def import_text(req: ImportTextRequest, kb: KBManager = Depends(get_kb)):
    entries = kb.import_text(text=req.text, category=req.category,
                             source=req.source, title_prefix=req.title_prefix)
    return {"success": True, "imported_count": len(entries),
            "entries": [{"id": e.id, "title": e.title} for e in entries]}

@router.get("/search")
async def search_kb(
    query: str = Query(...), category: Optional[str] = Query(None),
    top_k: int = Query(5), kb: KBManager = Depends(get_kb),
):
    results = kb.search(query=query, category=category, top_k=top_k)
    return {"query": query, "count": len(results),
            "results": [{"id": e.id, "title": e.title, "content": e.content,
                         "category": e.category, "tags": e.tags,
                         "confidence": e.confidence} for e in results]}

@router.get("/index")
async def get_index(kb: KBManager = Depends(get_kb)):
    return {"entries": kb.get_index()}

@router.put("/{entry_id}")
async def update_kb(entry_id: str, req: UpdateKBRequest,
                    kb: KBManager = Depends(get_kb)):
    try:
        entry = kb.update(entry_id, title=req.title, content=req.content,
                          tags=req.tags, confirmed=req.confirmed)
    except KBError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"success": True, "entry_id": entry.id, "updated_at": entry.updated_at}

@router.delete("/{entry_id}")
async def delete_kb(
    entry_id: str,
    req: DeleteKBRequest,
    kb: KBManager = Depends(get_kb),
):
    """Delete a KB entry. Body must include {"confirm": true} to execute."""
    if not req.confirm:
        raise HTTPException(
            status_code=400,
            detail="confirm must be true to execute deletion. Safety guard."
        )
    deleted = kb.delete(entry_id, confirm=True)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"KB entry '{entry_id}' not found.")
    return {"success": True, "entry_id": entry_id}

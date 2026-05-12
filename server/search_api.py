from __future__ import annotations
from fastapi import APIRouter, HTTPException
from server.schemas import SearchRequest

router = APIRouter()
_service = None


def init_search_api(svc):
    global _service
    _service = svc


@router.post("/api/search")
async def search(req: SearchRequest):
    if _service is None:
        raise HTTPException(503, "Service not ready")
    results = _service.rag.search_only(req.query, req.topk)
    return {
        "results": [
            {
                "score": r.score,
                "chunk_id": r.chunk_id,
                "title": r.title,
                "url": r.url,
                "author_hint": r.author_hint,
                "date_hint": r.date_hint,
                "text": r.text,
            }
            for r in results
        ]
    }

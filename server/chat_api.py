from __future__ import annotations
from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse
from server.schemas import ChatRequest, StopRequest

router = APIRouter()
_service = None


def init_chat_api(svc):
    global _service
    _service = svc


@router.post("/api/chat")
async def chat(req: ChatRequest):
    if _service is None:
        raise HTTPException(503, "Service not ready")
    return StreamingResponse(
        _service.stream_chat(
            req.session_id, req.message,
            api_key=req.api_key, base_url=req.base_url, model=req.model,
            temperature=req.temperature, max_tokens=req.max_tokens, top_p=req.top_p,
            topk=req.topk, max_candidates=req.max_candidates,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/chat/stop")
async def stop_chat(req: StopRequest):
    if _service is None:
        raise HTTPException(503, "Service not ready")
    _service.stop(req.session_id)
    return {"ok": True}

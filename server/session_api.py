from __future__ import annotations
from fastapi import APIRouter, HTTPException
from server.schemas import SessionCreate, SessionResponse, MessageResponse
from server import session_store

router = APIRouter()


@router.get("/api/sessions", response_model=list[SessionResponse])
async def list_sessions():
    return await session_store.list_sessions()


@router.post("/api/sessions", response_model=SessionResponse)
async def create_session(req: SessionCreate):
    return await session_store.create_session(req.title)


@router.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = await session_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(404, "Session not found")
    return {"ok": True}


@router.get("/api/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(session_id: str):
    return await session_store.get_messages(session_id)

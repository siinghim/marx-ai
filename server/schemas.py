from __future__ import annotations
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str
    message: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    topk: int | None = None
    max_candidates: int | None = None


class SearchRequest(BaseModel):
    query: str
    topk: int = Field(default=5, ge=1, le=50)


class StopRequest(BaseModel):
    session_id: str


class SessionCreate(BaseModel):
    title: str = Field(default="新对话")


class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    sources: list[dict]
    created_at: str

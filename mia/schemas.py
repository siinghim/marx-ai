# mia/schemas.py
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Doc:
    doc_id: str
    source_type: str  # "html" | "pdf"
    page_type: str  # "article" | "index" | "mixed" | "unknown"
    title: str
    url: str
    author_hint: str
    date_hint: str
    text: str
    raw_file: str
    text_hash: str
    char_count: int
    feature_debug: dict = field(default_factory=dict)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source_type: str
    page_type: str
    title: str
    url: str
    author_hint: str
    date_hint: str
    text: str


@dataclass
class RetrievalResult:
    score: float
    chunk_id: str
    doc_id: str
    source_type: str
    page_type: str
    title: str
    url: str
    author_hint: str
    date_hint: str
    text: str


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str
    sources: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

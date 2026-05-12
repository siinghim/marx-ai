# mia/chunker.py
from __future__ import annotations

from mia.schemas import Doc, Chunk


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    """Split text into overlapping chunks by paragraph boundaries."""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    cur = ""

    for p in paras:
        if len(cur) + len(p) + 1 <= chunk_size:
            cur += ("\n" if cur else "") + p
        else:
            if cur:
                chunks.append(cur)
            if len(p) <= chunk_size:
                cur = p
            else:
                start = 0
                while start < len(p):
                    chunks.append(p[start:start + chunk_size])
                    start += max(1, chunk_size - overlap)
                cur = ""

    if cur:
        chunks.append(cur)

    return [c for c in chunks if len(c.strip()) >= 80]


def chunk_doc(doc: Doc, chunk_size: int = 700, overlap: int = 100) -> list[Chunk]:
    """Chunk a single Doc into Chunk objects with metadata."""
    chunks: list[Chunk] = []
    for i, piece in enumerate(chunk_text(doc.text, chunk_size, overlap)):
        chunks.append(Chunk(
            chunk_id=f"{doc.doc_id}_{i}",
            doc_id=doc.doc_id,
            source_type=doc.source_type,
            page_type=doc.page_type,
            title=doc.title,
            url=doc.url,
            author_hint=doc.author_hint,
            date_hint=doc.date_hint,
            text=piece,
        ))
    return chunks


def chunk_docs(docs: list[Doc], chunk_size: int = 700, overlap: int = 100) -> list[Chunk]:
    """Chunk multiple Docs into a flat list of Chunks."""
    all_chunks: list[Chunk] = []
    for doc in docs:
        all_chunks.extend(chunk_doc(doc, chunk_size, overlap))
    return all_chunks

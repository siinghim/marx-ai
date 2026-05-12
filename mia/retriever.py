# mia/retriever.py
from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from mia.embedder import Embedder
from mia.schemas import RetrievalResult


class Retriever:
    """Search FAISS index with post-filtering and deduplication."""

    def __init__(
        self,
        index_dir: str | Path,
        embedder: Embedder,
    ):
        self.index_dir = Path(index_dir)
        self.embedder = embedder

        with (self.index_dir / "build_info.json").open("r", encoding="utf-8") as f:
            self.build_info = json.load(f)
        with (self.index_dir / "chunk_meta.json").open("r", encoding="utf-8") as f:
            self.meta: list[dict] = json.load(f)

        self._index = faiss.read_index(str(self.index_dir / self.build_info["index_file"]))

    def reload(self) -> None:
        """Hot-reload the index and metadata after incremental update."""
        with (self.index_dir / "build_info.json").open("r", encoding="utf-8") as f:
            self.build_info = json.load(f)
        with (self.index_dir / "chunk_meta.json").open("r", encoding="utf-8") as f:
            self.meta = json.load(f)
        self._index = faiss.read_index(str(self.index_dir / self.build_info["index_file"]))

    def search(
        self,
        query: str,
        topk: int = 5,
        max_candidates: int = 50,
        source_type: str = "all",
        page_type: str = "article",
        dedup_doc: bool = True,
    ) -> list[RetrievalResult]:
        q = self.embedder.encode_query([query])
        D, I = self._index.search(q, max_candidates)

        results: list[RetrievalResult] = []
        seen_docs: set[str] = set()

        for score, idx in zip(D[0], I[0]):
            item = self.meta[idx]

            if source_type != "all" and item.get("source_type") != source_type:
                continue
            if page_type != "all" and item.get("page_type", "") != page_type:
                continue

            if dedup_doc:
                doc_id = item.get("doc_id", "")
                if doc_id in seen_docs:
                    continue
                seen_docs.add(doc_id)

            results.append(RetrievalResult(
                score=float(score),
                chunk_id=item.get("chunk_id", ""),
                doc_id=item.get("doc_id", ""),
                source_type=item.get("source_type", ""),
                page_type=item.get("page_type", ""),
                title=item.get("title", ""),
                url=item.get("url", ""),
                author_hint=item.get("author_hint", ""),
                date_hint=item.get("date_hint", ""),
                text=item.get("text", ""),
            ))

            if len(results) >= topk:
                break

        return results

    @property
    def total_chunks(self) -> int:
        return self._index.ntotal

#!/usr/bin/env python3
"""
FAISS-based index builder for the MIA corpus.

Provides the IndexBuilder class with rebuild() and build_incremental()
methods. Uses IndexIDMap wrapping IndexFlatIP (inner product) for
embedding search.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

import faiss
import numpy as np
from tqdm import tqdm

from mia.chunker import chunk_docs
from mia.embedder import Embedder
from mia.schemas import Doc


# How many embeddings to encode before one faiss add_with_ids call
_ADD_BATCH_SIZE = 512


def _load_docs(path: Path) -> list[Doc]:
    """Load Doc objects from a JSONL file."""
    docs: list[Doc] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            docs.append(Doc(**data))
    return docs


def _append_jsonl(path: Path, records: list[dict]) -> None:
    """Append records to a JSONL file."""
    with path.open("a", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """Write records to a JSONL file (overwrite)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


class IndexBuilder:
    """Build and incrementally update a FAISS index for document chunks.

    Parameters
    ----------
    index_dir : str or Path
        Directory where index files (sample.index, chunk_meta.json,
        chunks.jsonl, build_info.json) are stored.
    embedder : Embedder
        Embedder instance used to encode chunk texts.
    """

    def __init__(self, index_dir: str | Path, embedder: Embedder):
        self.index_dir = Path(index_dir)
        self.embedder = embedder
        self.index_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------
    # rebuild
    # ----------------------------------------------------------------

    def rebuild(
        self,
        docs_path: str | Path,
        source_type: str | None = None,
        chunk_size: int = 700,
        overlap: int = 100,
        batch_size: int = 32,
        save_embeddings: bool = False,
    ) -> int:
        """Build a fresh FAISS index from a JSONL doc file.

        Parameters
        ----------
        docs_path : str or Path
            Path to docs_clean.jsonl (or similar) with one Doc per line.
        source_type : str or None
            Optional filter — only process docs whose source_type matches.
            ``None`` means process all docs.
        chunk_size : int
            Maximum characters per chunk.
        overlap : int
            Character overlap between consecutive chunks.
        batch_size : int
            Batch size for the embedder.
        save_embeddings : bool
            If True, also save the raw embedding array as ``embeddings.npy``.

        Returns
        -------
        int
            Number of chunks indexed.
        """
        docs_path = Path(docs_path)
        docs = _load_docs(docs_path)

        if source_type is not None:
            docs = [d for d in docs if d.source_type == source_type]

        # Chunk
        all_chunks = chunk_docs(docs, chunk_size=chunk_size, overlap=overlap)
        if not all_chunks:
            raise ValueError("No chunks produced — empty corpus?")

        texts = [c.text for c in all_chunks]
        meta_list = [asdict(c) for c in all_chunks]

        # Embed
        print(f"[indexer] encoding {len(texts)} chunks ...")
        embeddings = self.embedder.encode_documents(texts, batch_size=batch_size)
        dim = embeddings.shape[1]

        # Build FAISS index (inner product = cosine sim with normalized vecs)
        index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))
        ids = np.arange(len(all_chunks), dtype="int64")
        index.add_with_ids(embeddings, ids)
        print(f"[indexer] index has {index.ntotal} vectors, dim={dim}")

        # Save
        index_path = self.index_dir / "sample.index"
        faiss.write_index(index, str(index_path))

        meta_path = self.index_dir / "chunk_meta.json"
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(meta_list, f, ensure_ascii=False)

        chunks_path = self.index_dir / "chunks.jsonl"
        _write_jsonl(chunks_path, meta_list)

        build_info = {
            "index_file": "sample.index",
            "chunk_count": len(all_chunks),
            "model": self.embedder.model_name,
            "dim": dim,
            "chunk_size": chunk_size,
            "overlap": overlap,
            "source_type": source_type,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        info_path = self.index_dir / "build_info.json"
        with info_path.open("w", encoding="utf-8") as f:
            json.dump(build_info, f, ensure_ascii=False, indent=2)

        if save_embeddings:
            npy_path = self.index_dir / "embeddings.npy"
            np.save(str(npy_path), embeddings)

        print(f"[indexer] rebuild complete: {len(all_chunks)} chunks -> {index_path}")
        return len(all_chunks)

    # ----------------------------------------------------------------
    # incremental
    # ----------------------------------------------------------------

    def build_incremental(
        self,
        new_docs_path: str | Path,
        chunk_size: int = 700,
        overlap: int = 100,
        batch_size: int = 32,
    ) -> int:
        """Incrementally add new documents to an existing index.

        If no index exists yet, delegates to :meth:`rebuild`.

        Parameters
        ----------
        new_docs_path : str or Path
            Path to a JSONL file with new Doc records to add.
        chunk_size : int
            Maximum characters per chunk.
        overlap : int
            Character overlap between consecutive chunks.
        batch_size : int
            Batch size for the embedder.

        Returns
        -------
        int
            Number of *new* chunks added.
        """
        new_docs_path = Path(new_docs_path)

        # If no existing index, start fresh
        if not (self.index_dir / "build_info.json").exists():
            return self.rebuild(
                new_docs_path,
                source_type=None,
                chunk_size=chunk_size,
                overlap=overlap,
                batch_size=batch_size,
                save_embeddings=False,
            )

        # Load existing data
        with (self.index_dir / "build_info.json").open("r", encoding="utf-8") as f:
            build_info = json.load(f)

        with (self.index_dir / "chunk_meta.json").open("r", encoding="utf-8") as f:
            existing_meta: list[dict] = json.load(f)

        index = faiss.read_index(str(self.index_dir / build_info["index_file"]))
        next_id = existing_meta.__len__()

        # Load and chunk new docs
        new_docs = _load_docs(new_docs_path)
        new_chunks = chunk_docs(new_docs, chunk_size=chunk_size, overlap=overlap)
        if not new_chunks:
            print("[indexer] no new chunks to add")
            return 0

        texts = [c.text for c in new_chunks]
        new_meta = [asdict(c) for c in new_chunks]

        # Compute dedup: skip existing text_hash if stored in meta
        # (We don't store text_hash in meta, so this is approximate via faiss dup IDs)
        # Load existing chunk texts for dedup
        existing_texts: set[str] = set()
        for m in existing_meta:
            existing_texts.add(m.get("text", ""))

        truly_new: list[dict] = []
        truly_new_texts: list[str] = []
        for m, t in zip(new_meta, texts):
            if t not in existing_texts:
                truly_new.append(m)
                truly_new_texts.append(t)

        if not truly_new:
            print("[indexer] all new chunks are duplicates — nothing added")
            return 0

        # Embed new chunks
        print(f"[indexer] encoding {len(truly_new)} new chunks ...")
        embeddings = self.embedder.encode_documents(truly_new_texts, batch_size=batch_size)

        # Add to index
        add_ids = np.arange(next_id, next_id + len(truly_new), dtype="int64")
        index.add_with_ids(embeddings, add_ids)
        print(f"[indexer] index now has {index.ntotal} vectors")

        # Save updated index
        faiss.write_index(index, str(self.index_dir / "sample.index"))

        # Append to chunk_meta.json (replace in-memory and rewrite)
        existing_meta.extend(truly_new)
        with (self.index_dir / "chunk_meta.json").open("w", encoding="utf-8") as f:
            json.dump(existing_meta, f, ensure_ascii=False)

        # Append to chunks.jsonl
        _append_jsonl(self.index_dir / "chunks.jsonl", truly_new)

        # Update build_info
        build_info["chunk_count"] = len(existing_meta)
        build_info["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with (self.index_dir / "build_info.json").open("w", encoding="utf-8") as f:
            json.dump(build_info, f, ensure_ascii=False, indent=2)

        print(f"[indexer] incremental: added {len(truly_new)} chunks (skipped {len(new_chunks) - len(truly_new)} dupes)")
        return len(truly_new)

#!/usr/bin/env python3
"""
Spectre — Standalone FAISS Index Rebuild Script
================================================
Offline rebuild for CUDA 12.1 server. No network required after deps installed.

Usage:
  python rebuild.py --docs docs_merged.jsonl --out index_output --device cuda
"""

from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CHUNK_SIZE = 700
CHUNK_OVERLAP = 100
BATCH_SIZE = 32
MODEL_NAME = "BAAI/bge-m3"


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Spectre offline index rebuild")
    parser.add_argument("--docs", type=Path, required=True, help="merged docs JSONL")
    parser.add_argument("--out", type=Path, required=True, help="output index directory")
    parser.add_argument("--device", type=str, default="cuda", help="cuda or cpu")
    parser.add_argument("--model", type=str, default=MODEL_NAME, help="embedding model name")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    # 1. Load documents
    print(f"[1/4] Loading documents from {args.docs}...")
    docs = []
    with args.docs.open("r", encoding="utf-8") as f:
        for line in tqdm(f, desc="load docs", unit="lines"):
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    print(f"  Loaded {len(docs)} documents")

    # 2. Chunk documents
    print(f"[2/4] Chunking {len(docs)} documents (chunk_size={args.chunk_size}, overlap={args.overlap})...")
    all_chunks = []
    for doc in tqdm(docs, desc="chunk docs"):
        pieces = chunk_text(doc.get("text", ""), args.chunk_size, args.overlap)
        for i, piece in enumerate(pieces):
            all_chunks.append({
                "chunk_id": f'{doc["doc_id"]}_{i}',
                "doc_id": doc["doc_id"],
                "source_type": doc.get("source_type", ""),
                "page_type": doc.get("page_type", ""),
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "author_hint": doc.get("author_hint", ""),
                "date_hint": doc.get("date_hint", ""),
                "text": piece,
            })
    print(f"  Generated {len(all_chunks)} chunks")

    if not all_chunks:
        print("[ERROR] No chunks generated", file=sys.stderr)
        sys.exit(1)

    # 3. Build embeddings
    print(f"[3/4] Building embeddings with {args.model} on {args.device}...")
    device = args.device
    if device == "cuda" and not torch.cuda.is_available():
        print("  CUDA not available, falling back to CPU")
        device = "cpu"

    model = SentenceTransformer(args.model, device=device)
    texts = [c["text"] for c in all_chunks]

    embeddings = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    embeddings = np.asarray(embeddings, dtype="float32")
    dim = embeddings.shape[1]
    print(f"  Embeddings shape: {embeddings.shape}, dim={dim}")

    # 4. Build and save FAISS index
    print(f"[4/4] Building FAISS index ({len(all_chunks)} vectors, dim={dim})...")

    index = faiss.IndexIDMap(faiss.IndexFlatIP(dim))
    ids = np.arange(len(all_chunks), dtype="int64")

    # Add in sub-batches to avoid OOM
    sub_batch = 50000
    for start in tqdm(range(0, len(all_chunks), sub_batch), desc="add to index"):
        end = min(start + sub_batch, len(all_chunks))
        index.add_with_ids(embeddings[start:end], ids[start:end])

    print(f"  FAISS index built: {index.ntotal} vectors")

    # Save index
    index_path = args.out / "sample.index"
    faiss.write_index(index, str(index_path))
    print(f"  Index saved: {index_path}")

    # Save metadata
    meta_path = args.out / "chunk_meta.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False)

    chunks_path = args.out / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # Save build info
    build_info = {
        "docs_path": str(args.docs),
        "output_dir": str(args.out),
        "chunk_size": args.chunk_size,
        "overlap": args.overlap,
        "model": args.model,
        "batch_size": args.batch_size,
        "embedding_device": device,
        "docs_count": len(docs),
        "chunks_count": len(all_chunks),
        "embedding_dim": dim,
        "index_file": "sample.index",
        "meta_file": "chunk_meta.json",
        "chunks_file": "chunks.jsonl",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    info_path = args.out / "build_info.json"
    with info_path.open("w", encoding="utf-8") as f:
        json.dump(build_info, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] Index rebuilt: {len(all_chunks)} chunks -> {args.out}")
    print(f"  sample.index   : {index_path}")
    print(f"  chunk_meta.json: {meta_path}")
    print(f"  chunks.jsonl   : {chunks_path}")


if __name__ == "__main__":
    main()

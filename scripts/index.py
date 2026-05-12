#!/usr/bin/env python3
"""CLI wrapper for mia.indexer.IndexBuilder."""

import argparse
from pathlib import Path

from mia.embedder import Embedder
from mia.indexer import IndexBuilder


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--docs", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model", type=str, default="BAAI/bge-m3")
    p.add_argument("--device", type=str, default="auto")
    p.add_argument("--chunk-size", type=int, default=700)
    p.add_argument("--overlap", type=int, default=100)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--incremental", action="store_true")
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--save-embeddings", action="store_true")
    args = p.parse_args()

    embedder = Embedder(model_name=args.model, device=args.device)
    builder = IndexBuilder(args.out, embedder)

    if args.incremental:
        n = builder.build_incremental(
            args.docs,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            batch_size=args.batch_size,
        )
        print(f"[OK] incremental: added {n} chunks")
    else:
        n = builder.rebuild(
            args.docs,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            batch_size=args.batch_size,
            save_embeddings=args.save_embeddings,
        )
        print(f"[OK] rebuild: {n} chunks indexed")


if __name__ == "__main__":
    main()

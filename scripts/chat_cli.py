#!/usr/bin/env python3
"""Interactive chat CLI for querying the MIA index via a RAG service."""

import argparse
import asyncio
import os

from mia.config import load_config
from mia.rag import RAGService, format_sources


async def main_async(config_path: str):
    config = load_config(config_path)

    if not config.llm.api_key:
        config.llm.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not config.llm.api_key:
        raise SystemExit("[ERROR] No API key configured.")

    rag = RAGService(config)
    history = []

    print(f"[INFO] index: {config.index.dir}")
    print(f"[INFO] chunks: {rag.retriever.total_chunks}")
    print(f"[INFO] LLM: {config.llm.model}\n")
    print("Type /exit to quit, /clear to reset history.\n")

    while True:
        try:
            raw = input("问题> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break

        if raw in {"/exit", "/quit"}:
            break
        if raw == "/clear":
            history = []
            print("history cleared")
            continue
        if not raw:
            continue

        results = rag.retriever.search(
            raw,
            topk=config.index.topk,
            max_candidates=config.index.max_candidates,
        )
        print(f"\n[RETRIEVED {len(results)} chunks]")
        for i, r in enumerate(results):
            print(f"  [{i+1}] score={r.score:.4f} | {r.title[:60]}")

        print("\n[ANSWER]")
        async for token in rag.query(raw, history):
            print(token, end="", flush=True)
        print("\n")

        sources = format_sources(results)
        print("[SOURCES]")
        for s in sources:
            print(f"  [{s['index']}] {s['title']} | {s['url']}")
        print()

        history.append({"role": "user", "content": raw})
        history.append({"role": "assistant", "content": "[see above]"})
        if len(history) > config.sessions.max_history_turns * 2:
            history = history[-config.sessions.max_history_turns * 2:]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", type=str, default="config.yaml")
    args = p.parse_args()
    asyncio.run(main_async(args.config))


if __name__ == "__main__":
    main()

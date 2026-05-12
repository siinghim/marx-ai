# mia/rag.py
from __future__ import annotations

from collections.abc import AsyncIterator

from mia.config import AppConfig
from mia.embedder import Embedder
from mia.llm_client import LLMClient
from mia.retriever import Retriever, RetrievalResult


def build_context(results: list[RetrievalResult]) -> str:
    blocks = []
    for i, r in enumerate(results, start=1):
        header = [
            f"[{i}]",
            f"标题：{r.title}",
            f"URL：{r.url}",
        ]
        if r.author_hint:
            header.append(f"作者：{r.author_hint}")
        if r.date_hint:
            header.append(f"日期：{r.date_hint}")
        header.append("内容：")
        header.append(r.text)
        blocks.append("\n".join(header))
    return "\n\n".join(blocks)


def format_sources(results: list[RetrievalResult]) -> list[dict]:
    return [
        {
            "index": i,
            "title": r.title,
            "url": r.url,
            "chunk_id": r.chunk_id,
            "author_hint": r.author_hint,
            "date_hint": r.date_hint,
            "score": r.score,
        }
        for i, r in enumerate(results, start=1)
    ]


class RAGService:
    """Orchestrates retrieval + LLM generation."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.embedder = Embedder(
            model_name=config.embedding.model,
            device=config.embedding.device,
        )
        self.retriever = Retriever(
            index_dir=config.index.dir,
            embedder=self.embedder,
        )
        self.llm = LLMClient(config.llm)

    async def query(
        self,
        question: str,
        history: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        results = self.retriever.search(
            query=question,
            topk=self.config.index.topk,
            max_candidates=self.config.index.max_candidates,
        )
        context = build_context(results)
        hist = history or []
        hist = hist[-(self.config.sessions.max_history_turns * 2):]

        async for token in self.llm.chat_stream(
            question=question,
            context=context,
            history=hist,
        ):
            yield token

    def search_only(self, query: str, topk: int | None = None) -> list[RetrievalResult]:
        return self.retriever.search(
            query=query,
            topk=topk or self.config.index.topk,
            max_candidates=self.config.index.max_candidates,
        )

    def get_sources(self, results: list[RetrievalResult]) -> list[dict]:
        return format_sources(results)

    def reload_index(self) -> None:
        self.retriever.reload()

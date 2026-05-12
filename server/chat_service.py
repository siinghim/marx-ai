from __future__ import annotations

import asyncio
import json

from mia.config import load_config
from mia.rag import RAGService, build_context, format_sources
from server import session_store


class ChatService:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.rag: RAGService | None = None
        self._stop_flags: dict[str, asyncio.Event] = {}

    async def initialize(self) -> None:
        self.rag = RAGService(self.config)

    def get_stop_event(self, session_id: str) -> asyncio.Event:
        if session_id not in self._stop_flags:
            self._stop_flags[session_id] = asyncio.Event()
        return self._stop_flags[session_id]

    def stop(self, session_id: str) -> None:
        ev = self._stop_flags.get(session_id)
        if ev:
            ev.set()

    async def stream_chat(self, session_id: str, message: str):
        yield 'data: {"type": "status", "status": "retrieving"}\n\n'

        results = self.rag.retriever.search(
            query=message,
            topk=self.config.index.topk,
            max_candidates=self.config.index.max_candidates,
        )
        context = build_context(results)
        sources = format_sources(results)

        yield 'data: {"type": "status", "status": "generating"}\n\n'

        history = await session_store.get_messages(
            session_id, limit=self.config.sessions.max_history_turns * 2
        )
        llm_history = [{"role": m["role"], "content": m["content"]} for m in history]

        await session_store.add_message(session_id, "user", message, [])

        # Auto-title from first message
        all_msgs = await session_store.get_messages(session_id, limit=2)
        if len(all_msgs) == 1:
            title = message[:30] + ("..." if len(message) > 30 else "")
            await session_store.update_session_title(session_id, title)

        stop_ev = self.get_stop_event(session_id)
        stop_ev.clear()
        full_answer = ""

        async for token in self.rag.llm.chat_stream(
            question=message,
            context=context,
            history=llm_history,
        ):
            if stop_ev.is_set():
                full_answer += "\n\n[已停止生成]"
                break
            full_answer += token
            safe = json.dumps({"type": "token", "content": token}, ensure_ascii=False)
            yield f"data: {safe}\n\n"

        await session_store.add_message(session_id, "assistant", full_answer, sources)

        yield f"data: {json.dumps({'type': 'sources', 'sources': sources}, ensure_ascii=False)}\n\n"
        yield 'data: {"type": "done"}\n\n'

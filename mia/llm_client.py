# mia/llm_client.py
from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from mia.config import LLMConfig


SYSTEM_PROMPT = (
    "你是一个基于检索上下文回答问题的助手。"
    "请优先依据提供的文献片段作答，不要编造来源中没有的信息。"
    "如果检索材料不足以回答，请明确说明“根据当前检索到的材料，无法确定”。"
    "回答时尽量准确、简洁，并在结尾用“依据：[编号]”列出主要依据的片段编号。"
)


def build_user_prompt(question: str, context: str) -> str:
    return f"""用户问题：
{question}

检索到的文献片段：
{context}

请完成：
1. 用中文回答问题；
2. 优先依据给定文献片段；
3. 如果片段之间有差异，说明差异；
4. 结尾列出主要依据编号，格式如：依据：[1][3]。"""


class LLMClient:
    """Async wrapper around OpenAI-compatible chat/completions with streaming."""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)

    async def chat_stream(
        self,
        question: str,
        context: str,
        history: list[dict],
    ) -> AsyncIterator[str]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": build_user_prompt(question, context)})

        stream = await self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

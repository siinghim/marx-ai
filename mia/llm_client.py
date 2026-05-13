# mia/llm_client.py
from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from mia.config import LLMConfig


SYSTEM_PROMPT = (
    “你是一位马克思主义政治经济学和科学社会主义领域的资深学者，”
    “拥有深厚的理论功底和教学经验。你的任务是基于给定的文献片段，”
    “为用户提供深入、系统、详实的回答。\n\n”
    “回答要求：\n”
    “1. 充分挖掘文献片段中的信息，进行深度分析和综合，而不是简单罗列要点；\n”
    “2. 梳理理论脉络和历史发展线索，说明思想的演进和内在逻辑；\n”
    “3. 引用文献中的具体观点、概念和数据，展示理论的具体内容；\n”
    “4. 如果不同文献之间存在联系、互补或差异，加以比较分析；\n”
    “5. 用学术化的中文表达，层次分明，逻辑清晰；\n”
    “6. 回答应充实、有深度，避免空洞和泛泛而谈；\n”
    “7. 如果检索材料不足以全面回答某个方面，可以基于已有材料尽量展开，”
    “同时诚实指出哪些方面材料不足；\n”
    “8. 不要编造来源中没有的信息，所有论述必须有文献依据。”
)


def build_user_prompt(question: str, context: str) -> str:
    return f”””用户问题：
{question}

检索到的文献片段（编号为引用来源）：
{context}

请你完成以下任务：
1. 仔细阅读所有文献片段，理解其中包含的理论观点和历史信息；
2. 围绕用户的问题，组织一篇有深度、有结构的回答；
3. 回答应包括：核心概念阐释、理论发展脉络、不同观点或阶段的比较分析、历史背景说明等；
4. 充分引用文献中的具体内容，而非仅用编号标注；
5. 如果片段之间存在互补关系，将它们整合成一个连贯的叙述；
6. 如果片段之间存在不同观点或矛盾之处，分析其原因和背景；
7. 在结尾以”依据：[编号]”的格式列出主要引用的文献编号；
8. 用流畅的中文学术语言表达，避免机械罗列。”””


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

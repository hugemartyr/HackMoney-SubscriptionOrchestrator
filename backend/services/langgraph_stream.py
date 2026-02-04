from __future__ import annotations

from typing import Any, AsyncGenerator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from utils.config import load_config
from utils.prompts.loader import load_prompt


def build_llm() -> ChatGoogleGenerativeAI:
    config = load_config()
    return ChatGoogleGenerativeAI(
        google_api_key=config.llm_api_key,
        model=config.llm_model,
        temperature=0.2,
    )


async def stream_response(prompt: str, tool_results: list[dict[str, Any]]):
    master_prompt = load_prompt("master_prompt.txt")
    tool_prompt = load_prompt("tool_instructions.txt")
    llm = build_llm()

    system_message = SystemMessage(content=f"{master_prompt}\n\nTooling:\n{tool_prompt}")
    user_message = HumanMessage(
        content=f"{prompt}\n\nTool results:\n{tool_results}"
    )

    async for chunk in llm.astream([system_message, user_message]):
        yield chunk.content or ""

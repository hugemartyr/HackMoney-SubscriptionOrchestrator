from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    request_id: str = Field(..., description="Client-generated request id.")
    prompt: str = Field(..., description="User prompt for the LLM.")
    intent: Optional[str] = Field(None, description="Optional tool intent.")
    tool_args: Optional[dict[str, Any]] = Field(default=None, description="Arguments for tool execution.")
    stream: bool = Field(default=False, description="Stream response tokens when true.")


class AgentResponse(BaseModel):
    request_id: str
    response: str
    tools: list[dict[str, Any]]

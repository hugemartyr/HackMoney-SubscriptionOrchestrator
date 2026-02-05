from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class AgentPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20_000)


class DiffApproveRequest(BaseModel):
    runId: Optional[str] = Field(default=None, max_length=128)
    file: str = Field(..., min_length=1, max_length=4_096)
    approved: bool


class ApplyAllRequest(BaseModel):
    runId: Optional[str] = Field(default=None, max_length=128)
    approved: bool

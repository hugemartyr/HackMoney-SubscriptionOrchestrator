from __future__ import annotations

from pydantic import BaseModel, Field


class AgentPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=20_000)


class DiffApproveRequest(BaseModel):
    file: str = Field(..., min_length=1, max_length=4_096)
    approved: bool


class ApplyAllRequest(BaseModel):
    approved: bool

"""
Agent prompts package. Re-exports generic prompts and Yellow-specific prompts for backward compatibility.
"""

from agent.prompts.prompts import (
    build_planner_prompt,
    build_coder_prompt,
    build_context_check_prompt,
    build_import_analysis_prompt,
    build_research_prompt,
    build_error_analysis_prompt,
    build_summary_prompt,
    build_fix_plan_prompt,
    build_escalation_prompt,
)
from agent.prompts.yellow import YELLOW_PROMPTS_PLACEHOLDER

__all__ = [
    "build_planner_prompt",
    "build_coder_prompt",
    "build_context_check_prompt",
    "build_import_analysis_prompt",
    "build_research_prompt",
    "build_error_analysis_prompt",
    "build_summary_prompt",
    "build_fix_plan_prompt",
    "build_escalation_prompt",
    "YELLOW_PROMPTS_PLACEHOLDER",
]

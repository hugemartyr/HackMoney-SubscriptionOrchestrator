from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any
from uuid import uuid4


AGENT_DIR = Path(__file__).resolve().parents[2] / "tmp_agents"


AGENT_TEMPLATE = """\
from __future__ import annotations

import os
from google import genai


SYSTEM_PROMPT = """{system_prompt}"""


def main() -> None:
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL", "gemini-1.5-pro")
    if not api_key:
        raise RuntimeError("LLM_API_KEY is required to run this agent.")

    client = genai.Client(api_key=api_key)

    print("Agent ready. Type 'exit' to quit.")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break

        response = client.models.generate_content(
            model=model,
            contents=[
                {"role": "user", "parts": [SYSTEM_PROMPT]},
                {"role": "user", "parts": [user_input]},
            ],
        )
        print(f"Agent: {response.text}\n")


if __name__ == "__main__":
    main()
"""


def create_kb_agent(payload: dict[str, Any]) -> dict[str, Any]:
    AGENT_DIR.mkdir(parents=True, exist_ok=True)

    knowledge_base = payload.get("knowledge_base", "default-kb")
    agent_name = payload.get("agent_name", "KB Agent")

    system_prompt = textwrap.dedent(
        f"""
        You are {agent_name}, an assistant initialized for the knowledge base: {knowledge_base}.
        Provide concise, helpful answers and cite assumptions when needed.
        """
    ).strip()

    agent_id = uuid4().hex[:8]
    filename = f"agent_{agent_id}.py"
    agent_path = AGENT_DIR / filename
    agent_code = AGENT_TEMPLATE.format(system_prompt=system_prompt.replace('"""', '""'))
    agent_path.write_text(agent_code, encoding="utf-8")

    return {
        "tool": "create_kb_agent",
        "status": "initialized",
        "agent_name": agent_name,
        "knowledge_base": knowledge_base,
        "agent_file": str(agent_path),
        "run_command": f"python {agent_path}",
    }

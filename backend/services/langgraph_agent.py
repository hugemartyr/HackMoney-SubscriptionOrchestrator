from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.messages import HumanMessage, SystemMessage

from utils.config import load_config
from utils.prompts.loader import load_prompt
from utils.intent import detect_intent
from utils.tools import run_tool


class AgentState(TypedDict):
    prompt: str
    intent: str | None
    tool_args: dict[str, Any]
    tool_results: list[dict[str, Any]]
    response: str


def build_llm() -> ChatGoogleGenerativeAI:
    config = load_config()
    return ChatGoogleGenerativeAI(
        google_api_key=config.llm_api_key,
        model=config.llm_model,
        temperature=0.2,
    )


def route_intent(state: AgentState) -> AgentState:
    state["intent"] = state["intent"] or detect_intent(state["prompt"])
    return state


def tool_node(state: AgentState) -> AgentState:
    if state["intent"]:
        result = run_tool(state["intent"], state["tool_args"])  # type: ignore[arg-type]
        state["tool_results"] = [result]
    return state


def respond_node(state: AgentState) -> AgentState:
    master_prompt = load_prompt("master_prompt.txt")
    tool_prompt = load_prompt("tool_instructions.txt")
    llm = build_llm()

    system_message = SystemMessage(content=f"{master_prompt}\n\nTooling:\n{tool_prompt}")
    user_message = HumanMessage(
        content=f"{state['prompt']}\n\nTool results:\n{state['tool_results']}"
    )

    response = llm.invoke([system_message, user_message])
    state["response"] = response.content
    return state


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("route_intent", route_intent)
    graph.add_node("tool", tool_node)
    graph.add_node("respond", respond_node)

    graph.set_entry_point("route_intent")
    graph.add_edge("route_intent", "tool")
    graph.add_edge("tool", "respond")
    graph.add_edge("respond", END)

    return graph.compile()

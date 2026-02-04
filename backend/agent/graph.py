from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from langchain_core.messages import BaseMessage

# Define the Agent Code State
class AgentState(TypedDict):
    messages: List[BaseMessage]
    current_code: str
    errors: List[str]

# Define Nodes
def scanner_node(state: AgentState):
    # Reads file structure from sandbox
    return {"messages": ["Scanned files..."]}

def planner_node(state: AgentState):
    # Decides which files to edit
    return {"messages": ["Planning edit..."]}

def coder_node(state: AgentState):
    # Generates code using RAG + LLM
    return {"current_code": "new code..."}

def tester_node(state: AgentState):
    # Runs npm build
    return {"errors": []}

# Define Graph
workflow = StateGraph(AgentState)

workflow.add_node("scanner", scanner_node)
workflow.add_node("planner", planner_node)
workflow.add_node("coder", coder_node)
workflow.add_node("tester", tester_node)

workflow.set_entry_point("scanner")
workflow.add_edge("scanner", "planner")
workflow.add_edge("planner", "coder")
workflow.add_edge("coder", "tester")
workflow.add_edge("tester", END)

app_graph = workflow.compile()

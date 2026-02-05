from __future__ import annotations

from langgraph.graph import END, StateGraph

from agent.state import AgentState
from agent.nodes.scan import scan_node
from agent.nodes.read import read_files_node
from agent.nodes.plan import plan_node
from agent.nodes.propose import propose_changes_node
from agent.nodes.validate import validate_node

workflow = StateGraph(AgentState)
workflow.add_node("scan", scan_node)
workflow.add_node("read_files", read_files_node)
workflow.add_node("plan", plan_node)
workflow.add_node("propose_changes", propose_changes_node)
workflow.add_node("validate", validate_node)

workflow.set_entry_point("scan")
workflow.add_edge("scan", "read_files")
workflow.add_edge("read_files", "plan")
workflow.add_edge("plan", "propose_changes")
workflow.add_edge("propose_changes", "validate")
workflow.add_edge("validate", END)

app_graph = workflow.compile()

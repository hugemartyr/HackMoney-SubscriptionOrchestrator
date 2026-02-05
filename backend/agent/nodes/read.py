from agent.state import AgentState
from services.sandbox_fs_service import read_text_file

async def read_files_node(state: AgentState) -> AgentState:
    file_contents: dict[str, str] = {}
    for p in state.get("files_to_read", []):
        try:
            obj = await read_text_file(p)
        except Exception:
            continue
        file_contents[obj["path"]] = obj["content"]
    return {"file_contents": file_contents}

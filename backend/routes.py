import subprocess

import io
import json
import os
import zipfile

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from agent.runner import run_agent
from fastapi.responses import Response, StreamingResponse
from services.upload_service import upload_from_github
from services.pending_diff_service import clear_pending_diffs, list_pending_diffs, pop_pending_diff
from services.sandbox_fs_service import SKIP_DIRS, delete_file, get_file_tree, read_text_file, require_root, write_text_file
from utils.schemas.agent import AgentPromptRequest, ApplyAllRequest, DiffApproveRequest
from utils.schemas.upload import UploadRequest


router = APIRouter()

class FileWriteRequest(BaseModel):
    path: str
    content: str


@router.post("/upload")
async def upload(req: UploadRequest):
    # Validated by Pydantic schema (UploadRequest)
    github_url = str(req.github_url).strip()

    try:
        await upload_from_github(github_url)
        return {"ok": True}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="git clone timed out")
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or "unknown error").strip()
        raise HTTPException(status_code=400, detail=f"git clone failed: {msg}")


@router.get("/files/tree")
async def files_tree():
    tree = await get_file_tree()
    return {"tree": tree}


@router.get("/files/content")
async def file_content(path: str = Query(...)):
    return await read_text_file(path)


@router.put("/files/content")
async def put_file_content(req: FileWriteRequest):
    return await write_text_file(req.path, req.content)


@router.delete("/files")
async def delete_file_endpoint(path: str = Query(...)):
    return await delete_file(path)


@router.post("/api/yellow-agent/stream")
async def yellow_agent_stream(req: AgentPromptRequest):
    """
    Streams SSE events to the frontend. Each message is encoded as:
      data: <json>\n\n
    """

    async def gen():
        # Ensure sandbox exists early (gives a clean HTTP error before streaming).
        require_root()

        async for event in run_agent(req.prompt):
            payload = json.dumps(event, ensure_ascii=False)
            yield f"data: {payload}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)


@router.post("/api/diff/approve")
async def approve_diff(req: DiffApproveRequest):
    """
    Approve/reject a pending diff for a specific file.
    If approved, writes newCode into the sandbox.
    """
    diff = await pop_pending_diff(req.file)
    if diff is None:
        raise HTTPException(status_code=404, detail="No pending diff for file")

    if req.approved:
        await write_text_file(diff.file, diff.newCode)
        return {"ok": True, "applied": True, "file": diff.file}

    return {"ok": True, "applied": False, "file": diff.file}


@router.post("/api/yellow-agent/apply")
async def apply_all(req: ApplyAllRequest):
    """
    Keep/discard-all endpoint:
    - approved=true: apply all pending diffs
    - approved=false: discard all pending diffs
    """
    if not req.approved:
        await clear_pending_diffs()
        return {"ok": True, "applied": 0}

    diffs = await list_pending_diffs()
    applied = 0
    for d in diffs:
        await write_text_file(d.file, d.newCode)
        applied += 1
    await clear_pending_diffs()
    return {"ok": True, "applied": applied}


@router.get("/api/project/download")
async def download_project():
    """
    Zip the current sandbox root and return it as a download.
    """
    root = require_root()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip ignored dirs
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

            for filename in filenames:
                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, root)
                # Avoid absolute/parent references in zip entries
                if rel_path.startswith(".."):
                    continue
                zf.write(abs_path, arcname=rel_path)

    data = buf.getvalue()
    headers = {"Content-Disposition": 'attachment; filename="yellow-fied-project.zip"'}
    return Response(content=data, media_type="application/zip", headers=headers)


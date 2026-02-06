import asyncio
import subprocess

import io
import json
import os
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from agent.runner import resume_agent, run_agent
from config import settings
from fastapi.responses import Response, StreamingResponse
from services.upload_service import upload_from_github
from services.pending_diff_service import clear_pending_diffs, list_pending_diffs, pop_pending_diff
from services.sandbox_fs_service import SKIP_DIRS, delete_file, get_file_tree, read_text_file, require_root, write_text_file
from utils.logger import get_logger
from utils.schemas.agent import AgentPromptRequest, ApplyAllRequest, DiffApproveRequest, ResumeRequest
from utils.schemas.upload import UploadRequest


logger = get_logger(__name__)

router = APIRouter()

class FileWriteRequest(BaseModel):
    path: str
    content: str


class TerminalExecRequest(BaseModel):
    command: str


class TerminalExecResponse(BaseModel):
    stdout: list[str]
    stderr: list[str]
    exitCode: int


@router.post("/upload")
async def upload(req: UploadRequest):
    # Validated by Pydantic schema (UploadRequest)
    github_url = str(req.github_url).strip()
    logger.info("Received /upload request", extra={"github_url": github_url})

    try:
        await upload_from_github(github_url)
        logger.info("GitHub project uploaded successfully")
        return {"ok": True}
    except subprocess.TimeoutExpired:
        logger.info("Git clone timed out", extra={"github_url": github_url})
        raise HTTPException(status_code=408, detail="git clone timed out")
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or "unknown error").strip()
        logger.info("Git clone failed", extra={"github_url": github_url, "error": msg})
        raise HTTPException(status_code=400, detail=f"git clone failed: {msg}")


@router.post("/api/terminal/exec", response_model=TerminalExecResponse)
async def terminal_exec(req: TerminalExecRequest) -> TerminalExecResponse:
    """
    Execute a shell command inside the sandbox root directory.

    - The working directory is always the sandbox root returned by `require_root()`.
    - This is further validated against `settings.SANDBOX_DIR` to ensure we never
      escape the configured `/sandbox` folder.
    """
    logger.info("Received /api/terminal/exec request", extra={"command": req.command})

    root = require_root()
    sandbox_from_settings = Path(settings.SANDBOX_DIR).resolve()
    root_resolved = root.resolve()

    # Extra safety: ensure the runtime sandbox root matches config.
    if root_resolved != sandbox_from_settings:
        logger.info(
            "Sandbox root mismatch detected",
            extra={"root": str(root_resolved), "settings_sandbox_dir": str(sandbox_from_settings)},
        )
        raise HTTPException(status_code=500, detail="Sandbox root is not correctly configured")

    # Run the command in a thread to avoid blocking the event loop.
    try:
        completed: subprocess.CompletedProcess[str] = await asyncio.to_thread(
            subprocess.run,
            req.command,
            shell=True,
            cwd=root_resolved,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        logger.info("Terminal command timed out", extra={"command": req.command, "timeout_seconds": 30})
        raise HTTPException(status_code=408, detail="Command execution timed out")
    except Exception as e:  # pragma: no cover - safety net
        logger.info("Terminal command failed to start", extra={"command": req.command, "error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to execute command")

    stdout_lines = completed.stdout.splitlines() if completed.stdout else []
    stderr_lines = completed.stderr.splitlines() if completed.stderr else []

    logger.info(
        "Terminal command completed",
        extra={
            "command": req.command,
            "exit_code": completed.returncode,
            "stdout_lines": len(stdout_lines),
            "stderr_lines": len(stderr_lines),
        },
    )

    return TerminalExecResponse(stdout=stdout_lines, stderr=stderr_lines, exitCode=completed.returncode)


@router.get("/files/tree")
async def files_tree():
    logger.info("Received /files/tree request")
    tree = await get_file_tree()
    logger.info("Returning file tree", extra={"has_tree": bool(tree)})
    return {"tree": tree}


@router.get("/files/content")
async def file_content(path: str = Query(...)):
    logger.info("Received /files/content request", extra={"path": path})
    result = await read_text_file(path)
    logger.info("Returning file content", extra={"path": result.get("path")})
    return result


@router.put("/files/content")
async def put_file_content(req: FileWriteRequest):
    logger.info("Received PUT /files/content request", extra={"path": req.path})
    result = await write_text_file(req.path, req.content)
    logger.info("File write completed", extra={"path": result.get("path")})
    return result


@router.delete("/files")
async def delete_file_endpoint(path: str = Query(...)):
    logger.info("Received DELETE /files request", extra={"path": path})
    result = await delete_file(path)
    logger.info("File delete completed", extra={"path": result.get("path")})
    return result


@router.post("/api/yellow-agent/stream")
async def yellow_agent_stream(req: AgentPromptRequest):
    """
    Streams SSE events to the frontend. Each message is encoded as:
      data: <json>\n\n
    """

    logger.info(
        "Received /api/yellow-agent/stream request",
        extra={"prompt_length": len(req.prompt or ""), "has_run_id": bool(getattr(req, "runId", None))},
    )

    async def gen():
        # Ensure sandbox exists early (gives a clean HTTP error before streaming).
        require_root()
        logger.info("Sandbox root verified for yellow agent stream")

        run_id = uuid.uuid4().hex
        logger.info("Starting yellow agent run", extra={"runId": run_id})
        async for event in run_agent(run_id, req.prompt):
            payload = json.dumps(event, ensure_ascii=False)
            logger.info(
                "Streaming SSE event",
                extra={"runId": run_id, "event_type": event.get("type"), "keys": list(event.keys())},
            )
            yield f"data: {payload}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    logger.info("Returning StreamingResponse for yellow agent", extra={"headers": headers})
    return StreamingResponse(gen(), media_type="text/event-stream", headers=headers)


@router.post("/api/yellow-agent/resume")
async def yellow_agent_resume(req: ResumeRequest):
    """
    Resume the graph after HITL approval. Applies pending diffs if approved, then continues execution.
    """
    logger.info(
        "Received /api/yellow-agent/resume request",
        extra={"runId": req.runId, "approved": req.approved},
    )

    async def gen():
        require_root()
        approved_files: list[str] = []
        if req.approved:
            diffs = await list_pending_diffs(runId=req.runId)
            for d in diffs:
                await write_text_file(d.file, d.newCode)
                approved_files.append(d.file)
            await clear_pending_diffs(runId=req.runId)
            logger.info(
                "Applied pending diffs before resume",
                extra={"runId": req.runId, "applied": len(approved_files)},
            )
        else:
            await clear_pending_diffs(runId=req.runId)

        async for event in resume_agent(req.runId, req.approved, approved_files):
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
    logger.info(
        "Received /api/diff/approve request",
        extra={"file": req.file, "approved": req.approved, "runId": req.runId},
    )
    diff = await pop_pending_diff(req.file, runId=req.runId)
    if diff is None:
        logger.info(
            "No pending diff found for file on approval",
            extra={"file": req.file, "runId": req.runId},
        )
        raise HTTPException(status_code=404, detail="No pending diff for file")

    if req.approved:
        await write_text_file(diff.file, diff.newCode)
        logger.info(
            "Approved and applied diff",
            extra={"file": diff.file, "runId": req.runId},
        )
        return {"ok": True, "applied": True, "file": diff.file}

    logger.info(
        "Rejected diff (no changes applied)",
        extra={"file": diff.file, "runId": req.runId},
    )
    return {"ok": True, "applied": False, "file": diff.file}


@router.post("/api/yellow-agent/apply")
async def apply_all(req: ApplyAllRequest):
    """
    Keep/discard-all endpoint:
    - approved=true: apply all pending diffs
    - approved=false: discard all pending diffs
    """
    logger.info(
        "Received /api/yellow-agent/apply request",
        extra={"approved": req.approved, "runId": req.runId},
    )
    if not req.approved:
        await clear_pending_diffs(runId=req.runId)
        logger.info("Discarded all pending diffs", extra={"runId": req.runId})
        return {"ok": True, "applied": 0}

    diffs = await list_pending_diffs(runId=req.runId)
    applied = 0
    for d in diffs:
        await write_text_file(d.file, d.newCode)
        applied += 1
    await clear_pending_diffs(runId=req.runId)
    logger.info("Applied all pending diffs", extra={"runId": req.runId, "applied": applied})
    return {"ok": True, "applied": applied}


@router.get("/api/project/download")
async def download_project():
    """
    Zip the current sandbox root and return it as a download.
    """
    logger.info("Received /api/project/download request")
    root = require_root()
    logger.info("Preparing project zip from sandbox root", extra={"root": str(root)})

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
    logger.info(
        "Returning project zip download",
        extra={"size_bytes": len(data), "root": str(root)},
    )
    return Response(content=data, media_type="application/zip", headers=headers)


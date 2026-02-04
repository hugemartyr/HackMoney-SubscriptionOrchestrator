import subprocess

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.upload_service import upload_from_github
from services.sandbox_fs_service import delete_file, get_file_tree, read_text_file, write_text_file
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


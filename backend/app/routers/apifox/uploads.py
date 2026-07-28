"""Apifox 上传文件 · 路由（Binary body 用；项目作用域）。"""

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.routers.apifox.upload_schemas import UploadOut
from app.services.apifox import upload_service as service
from app.services.project_access_service import get_accessible_project

router = APIRouter(prefix="/apifox", tags=["接口自动化v2·上传文件"])


@router.post("/projects/{pid}/uploads", response_model=UploadOut)
async def upload_file(
    pid: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_accessible_project(db, pid, user)
    # 按 Content-Length 提前拒绝超大体，避免把整个大文件读进内存再报 400
    if int(request.headers.get("content-length") or 0) > service.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"文件超过 {service.MAX_UPLOAD_BYTES // (1024 * 1024)}MB 上限")
    data = await file.read()
    try:
        return service.create_upload(db, pid, file.filename or "file", file.content_type or "", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

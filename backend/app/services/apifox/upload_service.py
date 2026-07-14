"""Apifox 上传文件 · 业务层（Binary body 用）。

文件字节存 DB；限大小防 DB 膨胀。发送时按 file_id 取字节，校验属本项目。
"""

from typing import Callable, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.apifox.upload_file import ApifoxUploadFile
from app.repositories.apifox import upload_repo as repo
from app.routers.apifox.upload_schemas import UploadOut

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB，超出 400


def _out(f: ApifoxUploadFile) -> UploadOut:
    return UploadOut(
        id=f.id, filename=f.filename, content_type=f.content_type,
        size=f.size, created_at=f.created_at,
    )


def create_upload(db: Session, project_id: int, filename: str, content_type: str, data: bytes) -> UploadOut:
    if not data:
        raise ValueError("文件内容为空")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError(f"文件超过 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB 上限")
    obj = ApifoxUploadFile(
        project_id=project_id,
        filename=filename or "file",
        content_type=content_type or "application/octet-stream",
        size=len(data),
        data=data,
    )
    return _out(repo.add(db, obj))


def make_binary_loader(db: Session, project_id: int) -> Callable[[int], Optional[Tuple[bytes, str]]]:
    """给 build_request 注入的取字节回调：按 file_id 取，须属本项目，否则 None。"""
    def _load(file_id: int) -> Optional[Tuple[bytes, str]]:
        f = repo.get_file(db, file_id)
        if not f or f.project_id != project_id:
            return None
        return f.data, f.content_type
    return _load

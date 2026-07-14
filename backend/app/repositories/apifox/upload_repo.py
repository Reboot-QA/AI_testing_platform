"""Apifox 上传文件数据访问。"""

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.apifox.upload_file import ApifoxUploadFile


def add(db: Session, obj: ApifoxUploadFile) -> ApifoxUploadFile:
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_file(db: Session, file_id: int) -> Optional[ApifoxUploadFile]:
    return db.get(ApifoxUploadFile, file_id)


def list_id_created_by_project(db: Session, project_id: int) -> List[Tuple[int, datetime]]:
    """列本项目所有上传文件 (id, created_at)（GC 用，不取 data 字节）。"""
    rows = db.execute(
        select(ApifoxUploadFile.id, ApifoxUploadFile.created_at).where(
            ApifoxUploadFile.project_id == project_id
        )
    ).all()
    return [(r.id, r.created_at) for r in rows]


def delete_by_ids(db: Session, ids: List[int]) -> None:
    if not ids:
        return
    db.query(ApifoxUploadFile).filter(ApifoxUploadFile.id.in_(ids)).delete(synchronize_session=False)

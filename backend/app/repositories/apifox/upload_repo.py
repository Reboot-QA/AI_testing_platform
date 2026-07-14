"""Apifox 上传文件数据访问。"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.apifox.upload_file import ApifoxUploadFile


def add(db: Session, obj: ApifoxUploadFile) -> ApifoxUploadFile:
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_file(db: Session, file_id: int) -> Optional[ApifoxUploadFile]:
    return db.get(ApifoxUploadFile, file_id)

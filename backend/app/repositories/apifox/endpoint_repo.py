"""Apifox 接口管理 · 数据访问层（folder / endpoint）。

仅负责 CRUD 查询，不含业务校验（归属/权限在 service+router）。不提交事务，由 service 决定 commit。
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.endpoint import ApifoxEndpoint, ApifoxFolder


# ---------- folders ----------
def list_folders(db: Session, project_id: int) -> List[ApifoxFolder]:
    return (
        db.query(ApifoxFolder)
        .filter(ApifoxFolder.project_id == project_id)
        .order_by(ApifoxFolder.sort_order, ApifoxFolder.id)
        .all()
    )


def get_folder(db: Session, folder_id: int) -> Optional[ApifoxFolder]:
    return db.query(ApifoxFolder).filter(ApifoxFolder.id == folder_id).first()


def create_folder(db: Session, folder: ApifoxFolder) -> ApifoxFolder:
    db.add(folder)
    db.flush()
    return folder


def delete_folder(db: Session, folder: ApifoxFolder) -> None:
    db.delete(folder)


# ---------- endpoints ----------
def list_endpoints(db: Session, project_id: int) -> List[ApifoxEndpoint]:
    return (
        db.query(ApifoxEndpoint)
        .filter(ApifoxEndpoint.project_id == project_id)
        .order_by(ApifoxEndpoint.sort_order, ApifoxEndpoint.id)
        .all()
    )


def get_endpoint(db: Session, endpoint_id: int) -> Optional[ApifoxEndpoint]:
    return db.query(ApifoxEndpoint).filter(ApifoxEndpoint.id == endpoint_id).first()


def create_endpoint(db: Session, endpoint: ApifoxEndpoint) -> ApifoxEndpoint:
    db.add(endpoint)
    db.flush()
    return endpoint


def delete_endpoint(db: Session, endpoint: ApifoxEndpoint) -> None:
    db.delete(endpoint)


def count_child_folders(db: Session, parent_id: int) -> int:
    return db.query(ApifoxFolder).filter(ApifoxFolder.parent_id == parent_id).count()


def count_folder_endpoints(db: Session, folder_id: int) -> int:
    return db.query(ApifoxEndpoint).filter(ApifoxEndpoint.folder_id == folder_id).count()

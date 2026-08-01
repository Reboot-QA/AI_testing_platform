"""Apifox 接口管理 · 数据访问层（folder / endpoint）。

仅负责 CRUD 查询，不含业务校验（归属/权限在 service+router）。不提交事务，由 service 决定 commit。
"""

from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.apifox.endpoint import (
    ApifoxEndpoint,
    ApifoxEndpointAssertion,
    ApifoxEndpointExtract,
    ApifoxFolder,
)


def add(db: Session, obj):
    db.add(obj)
    db.flush()
    return obj


# ---------- folders ----------
def list_folders(db: Session, project_id: int) -> List[ApifoxFolder]:
    # 仅接口文件夹（kind=endpoint），避免场景文件夹泄漏进接口树
    return (
        db.query(ApifoxFolder)
        .filter(ApifoxFolder.project_id == project_id, ApifoxFolder.kind == "endpoint")
        .order_by(ApifoxFolder.sort_order, ApifoxFolder.id)
        .all()
    )


def get_folder(db: Session, folder_id: int) -> Optional[ApifoxFolder]:
    # 仅接口文件夹（kind=endpoint）：防接口侧路由/校验误挂载或删改场景文件夹
    return (
        db.query(ApifoxFolder)
        .filter(ApifoxFolder.id == folder_id, ApifoxFolder.kind == "endpoint")
        .first()
    )


def next_folder_sort_order(db: Session, project_id: int, parent_id: Optional[int]) -> int:
    """同层（同 parent_id）末尾的 sort_order + 1；空层返回 0。新建时排到最后用。"""
    q = db.query(func.max(ApifoxFolder.sort_order)).filter(
        ApifoxFolder.project_id == project_id, ApifoxFolder.kind == "endpoint"
    )
    q = q.filter(ApifoxFolder.parent_id.is_(None) if parent_id is None else ApifoxFolder.parent_id == parent_id)
    current_max = q.scalar()
    return current_max + 1 if current_max is not None else 0


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
        .filter(ApifoxEndpoint.project_id == project_id, ApifoxEndpoint.deleted_at.is_(None))
        .order_by(ApifoxEndpoint.sort_order, ApifoxEndpoint.id)
        .all()
    )


def next_endpoint_sort_order(db: Session, project_id: int, folder_id: Optional[int]) -> int:
    """同文件夹内末尾的 sort_order + 1；空文件夹返回 0。新建时排到最后用。"""
    q = db.query(func.max(ApifoxEndpoint.sort_order)).filter(
        ApifoxEndpoint.project_id == project_id, ApifoxEndpoint.deleted_at.is_(None)
    )
    q = q.filter(ApifoxEndpoint.folder_id.is_(None) if folder_id is None else ApifoxEndpoint.folder_id == folder_id)
    current_max = q.scalar()
    return current_max + 1 if current_max is not None else 0


def list_deleted_endpoints(db: Session, project_id: int) -> List[ApifoxEndpoint]:
    """回收站：项目内已软删除的接口（最近删的在前）。"""
    return (
        db.query(ApifoxEndpoint)
        .filter(ApifoxEndpoint.project_id == project_id, ApifoxEndpoint.deleted_at.is_not(None))
        .order_by(ApifoxEndpoint.deleted_at.desc(), ApifoxEndpoint.id.desc())
        .all()
    )


def get_endpoint(db: Session, endpoint_id: int) -> Optional[ApifoxEndpoint]:
    return db.query(ApifoxEndpoint).filter(ApifoxEndpoint.id == endpoint_id).first()


def clear_cases_stale(db: Session, endpoint_id: int) -> None:
    """接口用例被新增/编辑后清除「待复核」标记（表示已处理 Swagger 变更）。"""
    db.query(ApifoxEndpoint).filter(ApifoxEndpoint.id == endpoint_id).update(
        {ApifoxEndpoint.cases_stale: False}, synchronize_session=False
    )


def create_endpoint(db: Session, endpoint: ApifoxEndpoint) -> ApifoxEndpoint:
    db.add(endpoint)
    db.flush()
    return endpoint


def delete_endpoint(db: Session, endpoint: ApifoxEndpoint) -> None:
    db.delete(endpoint)


def count_child_folders(db: Session, parent_id: int) -> int:
    return db.query(ApifoxFolder).filter(ApifoxFolder.parent_id == parent_id).count()


def count_folder_endpoints(db: Session, folder_id: int) -> int:
    # 仅统计未软删除的接口：只剩回收站接口的文件夹应可删除
    return (
        db.query(ApifoxEndpoint)
        .filter(ApifoxEndpoint.folder_id == folder_id, ApifoxEndpoint.deleted_at.is_(None))
        .count()
    )


# ---------- 接口级处理器（断言/提取子表） ----------
def list_endpoint_assertions(db: Session, endpoint_id: int) -> List[ApifoxEndpointAssertion]:
    return (
        db.query(ApifoxEndpointAssertion)
        .filter(ApifoxEndpointAssertion.endpoint_id == endpoint_id)
        .order_by(ApifoxEndpointAssertion.sort_order, ApifoxEndpointAssertion.id)
        .all()
    )


def list_endpoint_extracts(db: Session, endpoint_id: int) -> List[ApifoxEndpointExtract]:
    return (
        db.query(ApifoxEndpointExtract)
        .filter(ApifoxEndpointExtract.endpoint_id == endpoint_id)
        .order_by(ApifoxEndpointExtract.sort_order, ApifoxEndpointExtract.id)
        .all()
    )


def delete_endpoint_assertions(db: Session, endpoint_id: int) -> None:
    db.query(ApifoxEndpointAssertion).filter(
        ApifoxEndpointAssertion.endpoint_id == endpoint_id
    ).delete()


def delete_endpoint_extracts(db: Session, endpoint_id: int) -> None:
    db.query(ApifoxEndpointExtract).filter(
        ApifoxEndpointExtract.endpoint_id == endpoint_id
    ).delete()

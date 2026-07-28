"""用户项目偏好（置顶 / 排序）数据访问。"""

from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.user_project_pref import UserProjectPref


def map_for_user(db: Session, user_id: int, project_ids: List[int]) -> Dict[int, UserProjectPref]:
    """取该用户对给定项目的偏好，按 project_id 索引；无偏好的项目不在结果里。"""
    if not project_ids:
        return {}
    rows = (
        db.query(UserProjectPref)
        .filter(UserProjectPref.user_id == user_id, UserProjectPref.project_id.in_(project_ids))
        .all()
    )
    return {r.project_id: r for r in rows}


def upsert(db: Session, user_id: int, project_id: int, pinned: bool, sort_order: int) -> None:
    """存在则更新，否则新建；不 commit（调用方统一提交）。"""
    row = (
        db.query(UserProjectPref)
        .filter(UserProjectPref.user_id == user_id, UserProjectPref.project_id == project_id)
        .first()
    )
    if row:
        row.pinned = pinned
        row.sort_order = sort_order
    else:
        db.add(
            UserProjectPref(
                user_id=user_id, project_id=project_id, pinned=pinned, sort_order=sort_order
            )
        )


def delete_by_project(db: Session, project_id: int) -> None:
    """删除某项目的全部用户偏好（项目硬删除时清理，避免 FK 阻塞/孤儿）。不 commit。"""
    db.query(UserProjectPref).filter(UserProjectPref.project_id == project_id).delete(
        synchronize_session=False
    )

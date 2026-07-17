"""项目成员管理 · 业务层（增删查 + 可加候选人）。

沿用存量项目模块"service 直接访问 DB"的风格。成员是显式授权记录，独立于部门可见性。
"""

from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas import ProjectMemberCandidateOut, ProjectMemberOut


def _dept_name(db: Session, department_id: Optional[int]) -> str:
    if not department_id:
        return ""
    dept = db.query(Department).filter(Department.id == department_id).first()
    return dept.name if dept else ""


def list_members(db: Session, project_id: int) -> List[ProjectMemberOut]:
    rows = (
        db.query(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .filter(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.asc())
        .all()
    )
    return [
        ProjectMemberOut(
            id=m.id,
            user_id=u.id,
            username=u.username,
            full_name=u.full_name,
            email=u.email,
            department_name=_dept_name(db, u.department_id),
            created_at=m.created_at,
        )
        for m, u in rows
    ]


def add_member(db: Session, project_id: int, user_id: int, actor_id: int) -> ProjectMemberOut:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    exists = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="该用户已是项目成员")
    member = ProjectMember(project_id=project_id, user_id=user_id, created_by=actor_id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return ProjectMemberOut(
        id=member.id,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        department_name=_dept_name(db, user.department_id),
        created_at=member.created_at,
    )


def remove_member(db: Session, project_id: int, user_id: int) -> bool:
    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if not member:
        return False
    db.delete(member)
    db.commit()
    return True


def list_candidates(db: Session, project_id: int, keyword: Optional[str]) -> List[ProjectMemberCandidateOut]:
    """可加入的用户：启用且尚未是成员；管理员用于成员选择器（owner 也需要，故不走 admin-only 用户接口）。"""
    member_ids = db.query(ProjectMember.user_id).filter(ProjectMember.project_id == project_id)
    query = db.query(User).filter(User.is_active.is_(True), User.id.notin_(member_ids))
    if keyword and keyword.strip():
        like = f"%{keyword.strip()}%"
        query = query.filter(or_(User.username.like(like), User.full_name.like(like)))
    users = query.order_by(User.username.asc()).limit(50).all()
    return [
        ProjectMemberCandidateOut(
            id=u.id,
            username=u.username,
            full_name=u.full_name,
            email=u.email,
            department_name=_dept_name(db, u.department_id),
        )
        for u in users
    ]

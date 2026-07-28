from typing import List

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Query, Session

from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User


def is_admin(user: User) -> bool:
    return user.role == "admin"


def is_project_manager(user: User, project: Project) -> bool:
    """能管理项目（改名/删项目/管成员）：系统管理员或项目创建者（owner）。"""
    return is_admin(user) or project.owner_id == user.id


def project_access_condition(user: User):
    if is_admin(user):
        return True
    conditions = [Project.owner_id == user.id]
    if user.department_id:
        conditions.append(Project.department_id == user.department_id)
    # 显式项目成员（跨部门授权，让被加入者仅获得该项目权限）
    conditions.append(Project.id.in_(select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)))
    return or_(*conditions)


def apply_project_access(query: Query, user: User) -> Query:
    if is_admin(user):
        return query
    return query.filter(project_access_condition(user))


def accessible_projects_query(db: Session, user: User) -> Query:
    return apply_project_access(db.query(Project), user)


def get_accessible_project_ids(db: Session, user: User) -> List[int]:
    return [project.id for project in accessible_projects_query(db, user).all()]


def get_accessible_project(db: Session, project_id: int, user: User) -> Project:
    project = accessible_projects_query(db, user).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def filter_joined_project(query: Query, user: User) -> Query:
    if is_admin(user):
        return query
    return query.filter(project_access_condition(user))

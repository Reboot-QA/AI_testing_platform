from typing import List

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models.project import Project
from app.models.user import User


def is_admin(user: User) -> bool:
    return user.role == "admin"


def project_access_condition(user: User):
    if is_admin(user):
        return True
    conditions = [Project.owner_id == user.id]
    if user.department_id:
        conditions.append(Project.department_id == user.department_id)
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

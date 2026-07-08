"""Workbench 重构 · 权限校验 v2（只认 组织 → 团队 → 项目 三级）。

完全不 import、不碰旧 project_access_service（部门共享逻辑原样留给存量模块）。
成员默认组织级（org_members 可见组织下全部项目）；project_members 存在时覆盖该项目角色。
系统 admin（User.role == "admin"）全通。

角色 → 动作：
  admin  : read write execute admin
  editor : read write execute
  viewer : read
组织成员未显式设 project_members 时，默认继承为 editor；组织 owner/admin 继承为 admin。
"""

from typing import List, Optional

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.models.workbench.tenant import OrgMember, ProjectMember, Team

_ROLE_ACTIONS = {
    "admin": {"read", "write", "execute", "admin"},
    "editor": {"read", "write", "execute"},
    "viewer": {"read"},
}


def _role_allows(role: str, action: str) -> bool:
    return action in _ROLE_ACTIONS.get(role, set())


def _user_org_ids(db: Session, user: User) -> List[int]:
    """用户所属组织（一人一组织，通常仅一个；以 org_members 为准，兼容 users.organization_id）。"""
    org_ids = {m.org_id for m in db.query(OrgMember).filter(OrgMember.user_id == user.id).all()}
    if user.organization_id:
        org_ids.add(user.organization_id)
    return list(org_ids)


def effective_role(db: Session, user: User, project: Project) -> Optional[str]:
    """解析用户对某项目的有效角色；无权限返回 None。"""
    if user.role == "admin":
        return "admin"

    # project_members 覆盖优先
    pm = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
        .first()
    )
    if pm:
        return pm.role

    # 组织级继承：项目团队所属组织是否在用户组织内
    if project.team_id is None:
        return None
    team = db.query(Team).filter(Team.id == project.team_id).first()
    if not team:
        return None
    if team.org_id not in _user_org_ids(db, user):
        return None

    om = (
        db.query(OrgMember)
        .filter(OrgMember.org_id == team.org_id, OrgMember.user_id == user.id)
        .first()
    )
    if om and om.role in ("owner", "admin"):
        return "admin"
    return "editor"  # 默认组织成员


def check_project_access(db: Session, user: User, project_id: int, action: str = "read") -> Project:
    """校验 user 对 project_id 是否有 action 权限；否则抛 404/403。返回 Project。"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    role = effective_role(db, user, project)
    if role is None or not _role_allows(role, action):
        raise HTTPException(status_code=403, detail="无权访问该项目")
    return project


def require_project_access(action: str = "read"):
    """FastAPI 依赖工厂：路由用 Depends(require_project_access("write"))，从路径 {pid} 取项目。

    B 侧所有项目作用域端点用它做归属+权限校验。返回 Project。
    """

    def dependency(
        pid: int,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ) -> Project:
        return check_project_access(db, user, pid, action)

    return dependency


def get_user_projects(db: Session, user: User) -> List[Project]:
    """当前用户可访问的项目列表（工作台/切换器用）。

    admin 全见；否则 = 其组织下所有项目 ∪ 有 project_members 的项目。
    """
    if user.role == "admin":
        return db.query(Project).order_by(Project.id.desc()).all()

    org_ids = _user_org_ids(db, user)
    team_ids = (
        [t.id for t in db.query(Team.id).filter(Team.org_id.in_(org_ids)).all()]
        if org_ids
        else []
    )
    pm_project_ids = [
        m.project_id for m in db.query(ProjectMember.project_id).filter(ProjectMember.user_id == user.id).all()
    ]

    query = db.query(Project)
    conds = []
    if team_ids:
        conds.append(Project.team_id.in_(team_ids))
    if pm_project_ids:
        conds.append(Project.id.in_(pm_project_ids))
    if not conds:
        return []
    from sqlalchemy import or_

    return query.filter(or_(*conds)).order_by(Project.id.desc()).all()

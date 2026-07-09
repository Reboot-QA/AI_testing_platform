"""Workbench 重构 · 工作台/项目契约端点（模块 A↔B 边界，第 1 周冻结）。

命名空间 /workbench，不撞旧 /projects/*、/api-automation/*。
仅提供「项目上下文 + 权限」给 B；所有资源型 CRUD 在后续 Phase 的项目作用域路由。
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.models.workbench.tenant import Organization, OrgMember, ProjectMember, Team
from app.services.workbench.access_service_v2 import (
    check_project_access,
    effective_role,
    get_user_projects,
)

router = APIRouter(prefix="/workbench", tags=["工作台"])


# ---------- 输出模型 ----------
class ProjectBrief(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    org_id: Optional[int] = None
    role: Optional[str] = None  # 当前用户对该项目的有效角色
    created_at: Optional[datetime] = None


class MemberOut(BaseModel):
    user_id: int
    username: str
    full_name: Optional[str] = None
    source: str  # project | org  —— 角色来源
    role: str


class ProjectDetail(ProjectBrief):
    owner_id: int
    owner_name: Optional[str] = None
    members: List[MemberOut] = []


# ---------- 辅助 ----------
def _team_org(db: Session, team_id: Optional[int]):
    if not team_id:
        return None, None
    team = db.query(Team).filter(Team.id == team_id).first()
    return team, (team.org_id if team else None)


def _brief(db: Session, project: Project, user: User) -> ProjectBrief:
    team, org_id = _team_org(db, project.team_id)
    return ProjectBrief(
        id=project.id,
        name=project.name,
        description=project.description,
        team_id=project.team_id,
        team_name=team.name if team else None,
        org_id=org_id,
        role=effective_role(db, user, project),
        created_at=project.created_at,
    )


# ---------- 端点 ----------
@router.get("/projects", response_model=List[ProjectBrief])
def list_workbench_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """当前用户可访问的项目列表（工作台 / 项目切换器）。"""
    projects = get_user_projects(db, current_user)
    return [_brief(db, p, current_user) for p in projects]


@router.get("/projects/{pid}", response_model=ProjectDetail)
def get_workbench_project(
    pid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """项目详情（团队 / 角色 / 成员）。校验 read 权限。"""
    project = check_project_access(db, current_user, pid, "read")
    brief = _brief(db, project, current_user)
    owner = db.query(User).filter(User.id == project.owner_id).first()
    return ProjectDetail(
        **brief.model_dump(),
        owner_id=project.owner_id,
        owner_name=owner.username if owner else None,
        members=_members(db, project),
    )


@router.get("/projects/{pid}/members", response_model=List[MemberOut])
def list_workbench_project_members(
    pid: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """项目成员与角色。校验 read 权限。"""
    project = check_project_access(db, current_user, pid, "read")
    return _members(db, project)


def _members(db: Session, project: Project) -> List[MemberOut]:
    """项目成员 = 显式 project_members ∪ 继承的组织成员（project_members 覆盖组织角色）。"""
    result: dict[int, MemberOut] = {}

    _, org_id = _team_org(db, project.team_id)
    if org_id is not None:
        rows = (
            db.query(OrgMember, User)
            .join(User, User.id == OrgMember.user_id)
            .filter(OrgMember.org_id == org_id)
            .all()
        )
        for om, user in rows:
            inherited = "admin" if om.role in ("owner", "admin") else "editor"
            result[user.id] = MemberOut(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                source="org",
                role=inherited,
            )

    pm_rows = (
        db.query(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .filter(ProjectMember.project_id == project.id)
        .all()
    )
    for pm, user in pm_rows:
        result[user.id] = MemberOut(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            source="project",
            role=pm.role,
        )

    return list(result.values())


# ---------- 组织 / 团队（会员管理建号下拉用；登录可见） ----------
class OrgBrief(BaseModel):
    id: int
    name: str


class TeamBrief(BaseModel):
    id: int
    name: str
    org_id: int


@router.get("/orgs", response_model=List[OrgBrief])
def list_orgs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """组织列表（建号时选择会员从属组织）。"""
    orgs = db.query(Organization).order_by(Organization.id).all()
    return [OrgBrief(id=o.id, name=o.name) for o in orgs]


@router.get("/orgs/{org_id}/teams", response_model=List[TeamBrief])
def list_org_teams(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """某组织下的团队列表（建号时选择会员从属团队）。"""
    teams = db.query(Team).filter(Team.org_id == org_id).order_by(Team.id).all()
    return [TeamBrief(id=t.id, name=t.name, org_id=t.org_id) for t in teams]

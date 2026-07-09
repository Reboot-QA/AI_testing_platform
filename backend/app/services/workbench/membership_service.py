"""Workbench 重构 · 会员租户写侧服务（建号/改号/删号绑定组织团队）。

只认组织级成员（org_members）+ 项目级覆盖（project_members）；团队作归属标签，不参与权限。
默认组织/团队的 get-or-create 逻辑在此集中，供 tenant_seed 回填与建号流程共用（避免重复）。
本模块不提交事务，由调用方 commit。
"""

from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workbench.tenant import Organization, OrgMember, ProjectMember, Team

DEFAULT_ORG_NAME = "默认组织"
DEFAULT_TEAM_NAME = "默认团队"

VALID_ORG_ROLES = {"owner", "admin", "member"}
# 建号/改号「表单」可分配的组织角色；owner 不经建号分配，保持单 owner（供路由层校验入参）。
ASSIGNABLE_ORG_ROLES = {"admin", "member"}


def resolve_default_org_team(db: Session) -> Tuple[Organization, Team]:
    """get-or-create 默认组织 + 默认团队；组织 owner 取第一个 admin，否则第一个用户。"""
    org = db.query(Organization).filter(Organization.name == DEFAULT_ORG_NAME).first()
    if not org:
        owner = (
            db.query(User).filter(User.role == "admin").order_by(User.id).first()
            or db.query(User).order_by(User.id).first()
        )
        if not owner:
            raise ValueError("无法创建默认组织：系统中还没有任何用户")
        org = Organization(name=DEFAULT_ORG_NAME, owner_user_id=owner.id)
        db.add(org)
        db.flush()

    team = (
        db.query(Team).filter(Team.org_id == org.id, Team.name == DEFAULT_TEAM_NAME).first()
    )
    if not team:
        team = Team(org_id=org.id, name=DEFAULT_TEAM_NAME)
        db.add(team)
        db.flush()

    return org, team


def bind_user_to_tenant(
    db: Session,
    user: User,
    organization_id: Optional[int] = None,
    team_id: Optional[int] = None,
    org_role: Optional[str] = None,
) -> None:
    """把 user 绑定到组织(必) + 团队(归属标签, 可空) + 组织角色；幂等，可重复调用重绑。

    未指定组织/团队时落到默认组织/默认团队。org_role 缺省 member。
    团队仅作归属标签，不参与权限判定（可见性仍是组织级）。
    """
    role = org_role or "member"
    if role not in VALID_ORG_ROLES:
        raise ValueError(f"无效的组织角色: {org_role}")

    if organization_id is None:
        org, default_team = resolve_default_org_team(db)
        organization_id = org.id
        if team_id is None:
            team_id = default_team.id
    else:
        if not db.query(Organization).filter(Organization.id == organization_id).first():
            raise ValueError("组织不存在")

    if team_id is not None:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team or team.org_id != organization_id:
            raise ValueError("团队不存在或不属于该组织")

    user.organization_id = organization_id
    user.team_id = team_id

    member = (
        db.query(OrgMember)
        .filter(OrgMember.org_id == organization_id, OrgMember.user_id == user.id)
        .first()
    )
    if member:
        member.role = role
    else:
        db.add(OrgMember(org_id=organization_id, user_id=user.id, role=role))


def unbind_user_tenant(db: Session, user_id: int) -> None:
    """删用户前清理其组织/项目成员行，消除 org_members/project_members 的 FK 悬挂。"""
    db.query(OrgMember).filter(OrgMember.user_id == user_id).delete(synchronize_session=False)
    db.query(ProjectMember).filter(ProjectMember.user_id == user_id).delete(
        synchronize_session=False
    )

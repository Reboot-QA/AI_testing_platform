"""Workbench 重构 · 存量数据回填（幂等，可重跑）。

策略：建 1 个默认组织 + 1 个默认团队，把存量用户挂为组织成员、存量项目挂到默认团队。
既满足「一人一组织」（全员单组织、无多组织切换），又保留灰度期「互相可见」行为
（组织成员默认继承 editor，等价旧部门共享）。
新用户建组织走惰性创建（Phase 2 工作台入口），本脚本只回填存量。
"""

import logging

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.database import engine
from app.models.project import Project
from app.models.user import User
from app.models.workbench.tenant import Organization, OrgMember, Team

logger = logging.getLogger(__name__)

DEFAULT_ORG_NAME = "默认组织"
DEFAULT_TEAM_NAME = "默认团队"


def seed_workbench_tenant(db: Session) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    # 依赖新表 + 加列均已就绪，否则跳过（下次启动补）
    required = {"organizations", "teams", "org_members", "project_members", "users", "projects"}
    if not required.issubset(table_names):
        return
    user_columns = {c["name"] for c in inspector.get_columns("users")}
    project_columns = {c["name"] for c in inspector.get_columns("projects")}
    if "organization_id" not in user_columns or "team_id" not in project_columns:
        logger.warning("Workbench 加列未完成，跳过租户回填")
        return

    # 组织 owner：优先第一个 admin，否则第一个用户
    owner = db.query(User).filter(User.role == "admin").order_by(User.id).first()
    if not owner:
        owner = db.query(User).order_by(User.id).first()
    if not owner:
        return  # 空库，无需回填

    org = db.query(Organization).filter(Organization.name == DEFAULT_ORG_NAME).first()
    if not org:
        org = Organization(name=DEFAULT_ORG_NAME, owner_user_id=owner.id)
        db.add(org)
        db.flush()

    team = (
        db.query(Team)
        .filter(Team.org_id == org.id, Team.name == DEFAULT_TEAM_NAME)
        .first()
    )
    if not team:
        team = Team(org_id=org.id, name=DEFAULT_TEAM_NAME)
        db.add(team)
        db.flush()

    changed = False

    # 用户：回填 organization_id + org_members
    for user in db.query(User).all():
        if user.organization_id is None:
            user.organization_id = org.id
            changed = True
        exists = (
            db.query(OrgMember)
            .filter(OrgMember.org_id == org.id, OrgMember.user_id == user.id)
            .first()
        )
        if not exists:
            if user.id == owner.id:
                role = "owner"
            elif user.role == "admin":
                role = "admin"
            else:
                role = "member"
            db.add(OrgMember(org_id=org.id, user_id=user.id, role=role))
            changed = True

    # 项目：回填 team_id
    for project in db.query(Project).filter(Project.team_id.is_(None)).all():
        project.team_id = team.id
        changed = True

    if changed:
        db.commit()
        logger.info("Workbench 租户回填完成：org=%s team=%s", org.id, team.id)

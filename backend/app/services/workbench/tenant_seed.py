"""Workbench 重构 · 存量数据回填（幂等，可重跑）。

策略：把存量用户挂到默认组织为成员、存量项目挂到默认团队，并回填 users.organization_id/team_id。
既满足「一人一组织」，又保留灰度期「互相可见」（组织成员默认继承 editor，等价旧部门共享）。
默认组织/团队的 get-or-create 复用 membership_service；新用户建号绑定见 bind_user_to_tenant。
"""

import logging

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.database import engine
from app.models.project import Project
from app.models.user import User
from app.models.workbench.tenant import OrgMember
from app.services.workbench.membership_service import resolve_default_org_team

logger = logging.getLogger(__name__)


def seed_workbench_tenant(db: Session) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    # 依赖新表 + 加列均已就绪，否则跳过（下次启动补）
    required = {"organizations", "teams", "org_members", "project_members", "users", "projects"}
    if not required.issubset(table_names):
        return
    user_columns = {c["name"] for c in inspector.get_columns("users")}
    project_columns = {c["name"] for c in inspector.get_columns("projects")}
    if (
        "organization_id" not in user_columns
        or "team_id" not in user_columns
        or "team_id" not in project_columns
    ):
        logger.warning("Workbench 加列未完成，跳过租户回填")
        return

    if not db.query(User).first():
        return  # 空库，无需回填

    org, team = resolve_default_org_team(db)
    owner_id = org.owner_user_id

    changed = False

    # 用户：回填 organization_id / team_id + org_members
    for user in db.query(User).all():
        if user.organization_id is None:
            user.organization_id = org.id
            changed = True
        if user.team_id is None:
            user.team_id = team.id
            changed = True
        exists = (
            db.query(OrgMember)
            .filter(OrgMember.org_id == org.id, OrgMember.user_id == user.id)
            .first()
        )
        if not exists:
            if user.id == owner_id:
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

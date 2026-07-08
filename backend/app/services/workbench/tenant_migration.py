"""Workbench 重构 · 加列迁移（幂等）。

新表（organizations/teams/org_members/project_members）由 create_all 建；
本迁移只负责给存量表 users/projects 加列，风格对齐 api_automation_migration。
不删列、不改语义；department_id 保留不动。
"""

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine


def migrate_workbench_tenant_columns(db: Session) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    statements = []

    if "users" in table_names:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "organization_id" not in user_columns:
            statements.append("ALTER TABLE users ADD COLUMN organization_id INTEGER")

    if "projects" in table_names:
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "team_id" not in project_columns:
            statements.append("ALTER TABLE projects ADD COLUMN team_id INTEGER")

    if statements:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
        db.expire_all()

"""项目模块幂等列迁移（create_all 只建新表；给"已存在但列不全"的表补列需手写）。

背景：演示等长生命周期库里可能残留旧的 project_members 表（仅 project_id/user_id），
create_all 遇到已存在的表会跳过、不补列，导致 SELECT created_by 报 1054 未知列。
"""

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine


def migrate_project_members_columns(db: Session) -> None:
    """project_members 补 created_by / created_at（历史残留表可能缺这两列）。"""
    inspector = inspect(engine)
    if "project_members" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("project_members")}
    with engine.begin() as conn:
        if "created_by" not in cols:
            conn.execute(text("ALTER TABLE project_members ADD COLUMN created_by INTEGER NULL"))
        if "created_at" not in cols:
            conn.execute(text("ALTER TABLE project_members ADD COLUMN created_at DATETIME NULL"))
    db.expire_all()

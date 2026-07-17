"""项目模块幂等列迁移（create_all 只建新表；已存在但结构不对的表需手工纠正）。

背景：演示等长生命周期库里残留过旧的 project_members 表（列不全、且 id 可能非自增），
create_all 遇到已存在的表会跳过，导致 SELECT created_by 报 1054、INSERT 因 id 无默认值报错。
该表完全归"项目成员"功能所有：为空时直接按模型重建（无数据可失，一次纠正全部结构问题）；
非空时保守地只补缺列，绝不动数据。
"""

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine
from app.models.project_member import ProjectMember


def migrate_project_members_columns(db: Session) -> None:
    inspector = inspect(engine)
    if "project_members" not in inspector.get_table_names():
        return

    row_count = db.execute(text("SELECT COUNT(*) FROM project_members")).scalar() or 0
    if row_count == 0:
        # 空表：按模型重建，保证自增 id / 全部列 / 唯一约束都正确（残留表可能都不对）
        ProjectMember.__table__.drop(engine, checkfirst=True)
        ProjectMember.__table__.create(engine, checkfirst=True)
        db.expire_all()
        return

    # 非空（正常库）：仅幂等补列，不动数据
    cols = {c["name"] for c in inspector.get_columns("project_members")}
    with engine.begin() as conn:
        if "created_by" not in cols:
            conn.execute(text("ALTER TABLE project_members ADD COLUMN created_by INTEGER NULL"))
        if "created_at" not in cols:
            conn.execute(text("ALTER TABLE project_members ADD COLUMN created_at DATETIME NULL"))
    db.expire_all()

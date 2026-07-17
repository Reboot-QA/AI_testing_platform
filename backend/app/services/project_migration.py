"""项目模块幂等列迁移（create_all 只建新表；已存在但结构不对的表需手工纠正）。

背景：演示等长生命周期库残留过旧的 project_members 表（列不全、id 可能非自增），
create_all 遇已存在表会跳过，导致 SELECT created_by 报 1054、INSERT 因 id 无默认值报错。
该表完全归"项目成员"功能所有：为空时直接按模型重建；非空时保守只补列、不动数据。

注意：count 与 DDL 必须走**同一条连接**。若用会话 db 先 SELECT（开事务持元数据锁）、
再用另一条连接 DROP（要独占锁），MySQL 下会自己等自己、无限挂起（sqlite 无此锁，测不出）。
整段兜异常：结构迁移失败绝不阻断应用启动。
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine
from app.models.project_member import ProjectMember

logger = logging.getLogger(__name__)


def migrate_project_members_columns(db: Session) -> None:
    try:
        inspector = inspect(engine)
        if "project_members" not in inspector.get_table_names():
            return
        existing = {c["name"] for c in inspector.get_columns("project_members")}

        # 同一条连接完成 count + DDL，避免与会话事务争元数据锁导致 DROP 挂起
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM project_members")).scalar() or 0
            if count == 0:
                # 空表：按模型重建，一次纠正自增 id / 全部列 / 唯一约束
                ProjectMember.__table__.drop(conn, checkfirst=True)
                ProjectMember.__table__.create(conn, checkfirst=True)
            else:
                # 非空（正常库）：仅补缺列，不动数据
                if "created_by" not in existing:
                    conn.execute(text("ALTER TABLE project_members ADD COLUMN created_by INTEGER NULL"))
                if "created_at" not in existing:
                    conn.execute(text("ALTER TABLE project_members ADD COLUMN created_at DATETIME NULL"))
            conn.commit()
        db.expire_all()
    except Exception:  # noqa: BLE001 - 结构迁移失败不得阻断应用启动
        logger.exception("project_members 结构迁移失败，已跳过")

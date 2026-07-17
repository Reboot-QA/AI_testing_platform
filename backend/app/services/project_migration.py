"""项目模块幂等列迁移（create_all 只建新表；已存在但结构不对的表需手工纠正）。

背景：演示等长生命周期库残留过旧的 project_members 表（列不全、id 可能非自增），
create_all 遇已存在表会跳过，导致 SELECT created_by 报 1054、INSERT 因 id 无默认值报错。
该表完全归"项目成员"功能所有：为空时按模型重建；非空时保守只补列、不动数据。

**绝不挂起启动**：DDL（尤其 DROP）要独占元数据锁，若被其它连接（如上次异常退出残留的
连接）持锁会一直等。故 MySQL 下设 lock_wait_timeout=5，拿不到锁就快速失败；count 后立即
commit 释放自身锁；整段兜异常——本迁移失败只记日志，绝不阻断应用启动。
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

        with engine.connect() as conn:
            if engine.dialect.name == "mysql":
                # DDL 抢不到元数据锁就 5s 失败，绝不挂起部署
                conn.execute(text("SET SESSION lock_wait_timeout = 5"))
            count = conn.execute(text("SELECT COUNT(*) FROM project_members")).scalar() or 0
            conn.commit()  # 释放 count 的共享元数据锁，DDL 只需与外部锁竞争

            if count == 0:
                ProjectMember.__table__.drop(conn, checkfirst=True)
                ProjectMember.__table__.create(conn, checkfirst=True)
            else:
                if "created_by" not in existing:
                    conn.execute(text("ALTER TABLE project_members ADD COLUMN created_by INTEGER NULL"))
                if "created_at" not in existing:
                    conn.execute(text("ALTER TABLE project_members ADD COLUMN created_at DATETIME NULL"))
            conn.commit()
        db.expire_all()
    except Exception:  # noqa: BLE001 - 结构迁移失败不得阻断应用启动
        logger.exception("project_members 结构迁移失败，已跳过（不阻断启动）")

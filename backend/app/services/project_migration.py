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


def _project_columns() -> set[str]:
    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns("projects")}


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


def migrate_project_last_import_url(db: Session) -> None:
    """为 projects 补 last_import_url（记住上次 OpenAPI 导入 URL，供同源更新识别 + 回填）。"""
    try:
        if "projects" not in inspect(engine).get_table_names():
            return
        if "last_import_url" in _project_columns():
            return
        with engine.connect() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(text("SET SESSION lock_wait_timeout = 5"))
            conn.execute(text("ALTER TABLE projects ADD COLUMN last_import_url VARCHAR(1000) NULL"))
            conn.commit()
        inspect(engine).clear_cache()
    except Exception:  # noqa: BLE001 - 结构迁移失败不得阻断应用启动
        logger.exception("projects.last_import_url 结构迁移失败，已跳过（不阻断启动）")


def migrate_project_owner_seq(db: Session) -> None:
    """为 projects 补 owner_seq：每个负责人名下从 1 递增（展示用序号，非全局主键）。"""
    if "projects" not in inspect(engine).get_table_names():
        return

    if "owner_seq" not in _project_columns():
        with engine.connect() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(text("SET SESSION lock_wait_timeout = 5"))
            conn.execute(text("ALTER TABLE projects ADD COLUMN owner_seq INTEGER NULL"))
            conn.commit()
        inspect(engine).clear_cache()

    if "owner_seq" not in _project_columns():
        raise RuntimeError("projects.owner_seq 列添加失败，请检查 MySQL 锁等待或执行权限")

    with engine.begin() as conn:
        owner_rows = conn.execute(text("SELECT DISTINCT owner_id FROM projects")).fetchall()
        for (owner_id,) in owner_rows:
            if owner_id is None:
                continue
            project_rows = conn.execute(
                text("SELECT id FROM projects WHERE owner_id = :owner_id ORDER BY id ASC"),
                {"owner_id": owner_id},
            ).fetchall()
            for idx, (project_id,) in enumerate(project_rows, start=1):
                conn.execute(
                    text("UPDATE projects SET owner_seq = :seq WHERE id = :project_id"),
                    {"seq": idx, "project_id": project_id},
                )

    db.expire_all()
    logger.info("projects.owner_seq 迁移完成")

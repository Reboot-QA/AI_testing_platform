"""hub_ai_tasks 表结构幂等迁移。"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine

logger = logging.getLogger(__name__)


def migrate_hub_ai_tasks_columns(db: Session) -> None:
    try:
        inspector = inspect(engine)
        if "hub_ai_tasks" not in inspector.get_table_names():
            return
        cols = {c["name"] for c in inspector.get_columns("hub_ai_tasks")}
        if "updated_at" in cols:
            return
        with engine.connect() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(text("SET SESSION lock_wait_timeout = 5"))
            conn.execute(
                text("ALTER TABLE hub_ai_tasks ADD COLUMN updated_at DATETIME NULL")
            )
            conn.execute(
                text("UPDATE hub_ai_tasks SET updated_at = created_at WHERE updated_at IS NULL")
            )
            conn.commit()
        inspect(engine).clear_cache()
        db.expire_all()
    except Exception:
        logger.exception("hub_ai_tasks.updated_at 列添加失败，已跳过（可重启 backend 重试）")


def migrate_hub_ai_requirement_item_imported_at(db: Session) -> None:
    try:
        inspector = inspect(engine)
        if "hub_ai_task_requirement_items" not in inspector.get_table_names():
            return
        cols = {c["name"] for c in inspector.get_columns("hub_ai_task_requirement_items")}
        if "imported_at" in cols:
            return
        with engine.connect() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(text("SET SESSION lock_wait_timeout = 5"))
            conn.execute(
                text("ALTER TABLE hub_ai_task_requirement_items ADD COLUMN imported_at DATETIME NULL")
            )
            conn.commit()
        inspect(engine).clear_cache()
        db.expire_all()
    except Exception:
        logger.exception("hub_ai_task_requirement_items.imported_at 列添加失败，已跳过")


def migrate_hub_ai_requirement_item_requirement_id(db: Session) -> None:
    try:
        inspector = inspect(engine)
        if "hub_ai_task_requirement_items" not in inspector.get_table_names():
            return
        cols = {c["name"] for c in inspector.get_columns("hub_ai_task_requirement_items")}
        if "requirement_id" in cols:
            return
        with engine.connect() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(text("SET SESSION lock_wait_timeout = 5"))
            conn.execute(
                text(
                    "ALTER TABLE hub_ai_task_requirement_items "
                    "ADD COLUMN requirement_id INT NULL, ADD INDEX ix_hub_ai_task_requirement_items_requirement_id (requirement_id)"
                )
            )
            conn.commit()
        inspect(engine).clear_cache()
        db.expire_all()
    except Exception:
        logger.exception("hub_ai_task_requirement_items.requirement_id 列添加失败，已跳过")


def migrate_hub_ai_task_progress_at(db: Session) -> None:
    try:
        inspector = inspect(engine)
        if "hub_ai_tasks" not in inspector.get_table_names():
            return
        cols = {c["name"] for c in inspector.get_columns("hub_ai_tasks")}
        if "progress_at" in cols:
            return
        with engine.connect() as conn:
            if engine.dialect.name == "mysql":
                conn.execute(text("SET SESSION lock_wait_timeout = 5"))
            conn.execute(text("ALTER TABLE hub_ai_tasks ADD COLUMN progress_at DATETIME NULL"))
            conn.execute(
                text(
                    "UPDATE hub_ai_tasks SET progress_at = COALESCE(updated_at, created_at) "
                    "WHERE progress_at IS NULL"
                )
            )
            conn.commit()
        inspect(engine).clear_cache()
        db.expire_all()
    except Exception:
        logger.exception("hub_ai_tasks.progress_at 列添加失败，已跳过")

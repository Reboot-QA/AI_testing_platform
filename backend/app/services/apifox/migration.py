"""Apifox 模块幂等列迁移（create_all 只建新表，给已有表加列需手写）。"""

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine


def migrate_apifox_endpoint_server_name(db: Session) -> None:
    """apifox_endpoints 加 server_name 列（选用的命名前置 URL 名）。mysql/sqlite 均支持简单加列。"""
    inspector = inspect(engine)
    if "apifox_endpoints" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_endpoints")}
    if "server_name" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_endpoints ADD COLUMN server_name VARCHAR(100)"))
    db.expire_all()


def migrate_apifox_assertion_operator(db: Session) -> None:
    """apifox_case_assertions 加 operator 列（断言比较操作符，默认 eq）。"""
    inspector = inspect(engine)
    if "apifox_case_assertions" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_case_assertions")}
    if "operator" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_case_assertions ADD COLUMN operator VARCHAR(20) NOT NULL DEFAULT 'eq'"))
    db.expire_all()

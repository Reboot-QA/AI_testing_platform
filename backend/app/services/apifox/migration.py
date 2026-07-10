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

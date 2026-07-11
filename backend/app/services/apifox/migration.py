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


def migrate_apifox_endpoint_contract(db: Session) -> None:
    """apifox_endpoints 加 response_schema_id（绑定响应模型）与 contract_strict（契约不符是否判失败）。"""
    inspector = inspect(engine)
    if "apifox_endpoints" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_endpoints")}
    with engine.begin() as conn:
        if "response_schema_id" not in cols:
            conn.execute(text("ALTER TABLE apifox_endpoints ADD COLUMN response_schema_id INTEGER"))
        if "contract_strict" not in cols:
            conn.execute(text("ALTER TABLE apifox_endpoints ADD COLUMN contract_strict BOOLEAN NOT NULL DEFAULT 0"))
    db.expire_all()


def migrate_apifox_run_step_contract(db: Session) -> None:
    """apifox_run_steps 加 contract_result（契约校验结果 JSON）。"""
    inspector = inspect(engine)
    if "apifox_run_steps" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_run_steps")}
    if "contract_result" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_run_steps ADD COLUMN contract_result TEXT"))
    db.expire_all()


def migrate_apifox_scenario_step_tree(db: Session) -> None:
    """apifox_scenario_steps 加 parent_step_id（控制步骤嵌套父）与 config（控制步骤配置 JSON）。"""
    inspector = inspect(engine)
    if "apifox_scenario_steps" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_scenario_steps")}
    with engine.begin() as conn:
        if "parent_step_id" not in cols:
            conn.execute(text("ALTER TABLE apifox_scenario_steps ADD COLUMN parent_step_id INTEGER"))
        if "config" not in cols:
            conn.execute(text("ALTER TABLE apifox_scenario_steps ADD COLUMN config TEXT"))
    db.expire_all()


def migrate_apifox_run_step_depth(db: Session) -> None:
    """apifox_run_steps 加 depth（步骤在场景树中的嵌套深度，供报告缩进）。"""
    inspector = inspect(engine)
    if "apifox_run_steps" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_run_steps")}
    if "depth" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_run_steps ADD COLUMN depth INTEGER NOT NULL DEFAULT 0"))
    db.expire_all()

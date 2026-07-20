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


def migrate_apifox_optimistic_version(db: Session) -> None:
    """给需乐观锁的 apifox 表加 version 列（默认 1）。"""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in (
            "apifox_endpoint_cases", "apifox_scenarios", "apifox_endpoints",
            "apifox_scripts", "apifox_schemas", "apifox_datasets", "apifox_suites",
        ):
            if table not in tables:
                continue
            cols = {c["name"] for c in inspector.get_columns(table)}
            if "version" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN version INTEGER NOT NULL DEFAULT 1"))
    db.expire_all()


def migrate_apifox_case_category(db: Session) -> None:
    """apifox_endpoint_cases 加 category 列（用例分类，默认 other）。"""
    inspector = inspect(engine)
    if "apifox_endpoint_cases" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_endpoint_cases")}
    if "category" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_endpoint_cases ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT 'other'"))
    db.expire_all()


def migrate_apifox_scenario_run_config(db: Session) -> None:
    """apifox_scenarios 加 run_config（场景运行配置 JSON：循环次数 / 绑数据集驱动）。"""
    inspector = inspect(engine)
    if "apifox_scenarios" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_scenarios")}
    if "run_config" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_scenarios ADD COLUMN run_config TEXT"))
    db.expire_all()


def migrate_apifox_run_iteration(db: Session) -> None:
    """apifox_run_steps 加 iteration（步骤所属轮次）、apifox_runs 加 iterations_meta（每组注入数据）。"""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "apifox_run_steps" in tables:
            cols = {c["name"] for c in inspector.get_columns("apifox_run_steps")}
            if "iteration" not in cols:
                conn.execute(text("ALTER TABLE apifox_run_steps ADD COLUMN iteration INTEGER NOT NULL DEFAULT 0"))
        if "apifox_runs" in tables:
            cols = {c["name"] for c in inspector.get_columns("apifox_runs")}
            if "iterations_meta" not in cols:
                conn.execute(text("ALTER TABLE apifox_runs ADD COLUMN iterations_meta TEXT"))
    db.expire_all()


def migrate_apifox_run_parent(db: Session) -> None:
    """apifox_runs 加 parent_run_id（套件运行的父运行 id，供父+子两级报告）。"""
    inspector = inspect(engine)
    if "apifox_runs" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_runs")}
    if "parent_run_id" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_runs ADD COLUMN parent_run_id INTEGER"))
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


def migrate_apifox_schedule_cron(db: Session) -> None:
    """apifox_schedules 加 cron_expr（schedule_type=cron 时的表达式）。"""
    inspector = inspect(engine)
    if "apifox_schedules" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_schedules")}
    if "cron_expr" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_schedules ADD COLUMN cron_expr VARCHAR(120)"))
    db.expire_all()


def migrate_apifox_scenario_priority(db: Session) -> None:
    """apifox_scenarios 加 priority（场景优先级：high/medium/low）。"""
    inspector = inspect(engine)
    if "apifox_scenarios" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_scenarios")}
    if "priority" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_scenarios ADD COLUMN priority VARCHAR(10) NOT NULL DEFAULT 'medium'"))
    db.expire_all()


def migrate_apifox_folder_kind(db: Session) -> None:
    """apifox_folders 加 kind（区分 endpoint / scenario 文件夹；存量默认 endpoint）。"""
    inspector = inspect(engine)
    if "apifox_folders" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_folders")}
    if "kind" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_folders ADD COLUMN kind VARCHAR(20) NOT NULL DEFAULT 'endpoint'"))
    db.expire_all()


def migrate_apifox_scenario_folder(db: Session) -> None:
    """apifox_scenarios 加 folder_id（所属场景文件夹；NULL=未分组）。"""
    inspector = inspect(engine)
    if "apifox_scenarios" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_scenarios")}
    if "folder_id" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_scenarios ADD COLUMN folder_id INTEGER"))
    db.expire_all()


def migrate_apifox_run_step_warnings(db: Session) -> None:
    """apifox_run_steps 加 warnings（诊断告警 JSON 列表，如 Binary 孤儿文件）。"""
    inspector = inspect(engine)
    if "apifox_run_steps" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_run_steps")}
    if "warnings" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE apifox_run_steps ADD COLUMN warnings TEXT"))
    db.expire_all()


def migrate_apifox_ordered_processors(db: Session) -> None:
    """apifox_endpoint_cases / apifox_endpoints 加 pre_processors/post_processors（有序处理器 JSON）。"""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table in ("apifox_endpoint_cases", "apifox_endpoints"):
            if table not in tables:
                continue
            cols = {c["name"] for c in inspector.get_columns(table)}
            if "pre_processors" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN pre_processors TEXT"))
            if "post_processors" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN post_processors TEXT"))
    db.expire_all()


def migrate_apifox_notify_retry(db: Session) -> None:
    """apifox_notify_configs 加 retry_count/retry_interval_sec（定时任务失败自动重试，项目级）。"""
    inspector = inspect(engine)
    if "apifox_notify_configs" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("apifox_notify_configs")}
    with engine.begin() as conn:
        if "retry_count" not in cols:
            conn.execute(text("ALTER TABLE apifox_notify_configs ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0"))
        if "retry_interval_sec" not in cols:
            conn.execute(
                text("ALTER TABLE apifox_notify_configs ADD COLUMN retry_interval_sec INTEGER NOT NULL DEFAULT 5")
            )
    db.expire_all()

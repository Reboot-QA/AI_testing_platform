import logging

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine

logger = logging.getLogger(__name__)


def _set_mysql_lock_timeouts(conn) -> None:
    if engine.dialect.name == "mysql":
        conn.execute(text("SET SESSION lock_wait_timeout = 10"))
        conn.execute(text("SET SESSION innodb_lock_wait_timeout = 10"))


def _backfill_sort_order(table: str) -> None:
    """批量回填 sort_order=0 的行（MySQL 8 ROW_NUMBER；SQLite 退化为逐行）。"""
    dialect = engine.dialect.name
    with engine.begin() as conn:
        _set_mysql_lock_timeouts(conn)
        if dialect == "mysql":
            conn.execute(
                text(
                    f"""
                    UPDATE {table} AS t
                    INNER JOIN (
                        SELECT r0.id,
                               COALESCE(pm.max_so, 0)
                                 + ROW_NUMBER() OVER (PARTITION BY r0.project_id ORDER BY r0.id) AS new_sort
                        FROM {table} AS r0
                        INNER JOIN (
                            SELECT project_id, MAX(sort_order) AS max_so
                            FROM {table}
                            GROUP BY project_id
                        ) AS pm ON pm.project_id = r0.project_id
                        WHERE r0.sort_order = 0
                    ) AS calc ON t.id = calc.id
                    SET t.sort_order = calc.new_sort
                    """
                )
            )
            return

        project_rows = conn.execute(text(f"SELECT DISTINCT project_id FROM {table}")).fetchall()
        for (project_id,) in project_rows:
            if project_id is None:
                continue
            max_seq = conn.execute(
                text(f"SELECT COALESCE(MAX(sort_order), 0) FROM {table} WHERE project_id = :project_id"),
                {"project_id": project_id},
            ).scalar()
            zero_rows = conn.execute(
                text(
                    f"SELECT id FROM {table} "
                    "WHERE project_id = :project_id AND sort_order = 0 "
                    "ORDER BY id ASC"
                ),
                {"project_id": project_id},
            ).fetchall()
            for offset, (row_id,) in enumerate(zero_rows, start=1):
                conn.execute(
                    text(f"UPDATE {table} SET sort_order = :sort_order WHERE id = :row_id"),
                    {"sort_order": int(max_seq or 0) + offset, "row_id": row_id},
                )


def _requirement_columns() -> set[str]:
    inspector = inspect(engine)
    if "requirements" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("requirements")}


def _testcase_columns() -> set[str]:
    inspector = inspect(engine)
    if "testcases" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("testcases")}


def migrate_requirement_created_by(db: Session) -> None:
    inspector = inspect(engine)
    if "requirements" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("requirements")}
    if "created_by_id" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE requirements ADD COLUMN created_by_id INTEGER"))


def migrate_requirement_sort_order(db: Session) -> None:
    """回填 requirements.sort_order。DDL 在 entrypoint 预迁移阶段执行，避免与 SQLAlchemy 连接争锁。"""
    if "requirements" not in inspect(engine).get_table_names():
        return
    if "sort_order" not in _requirement_columns():
        logger.warning("requirements.sort_order 列不存在，跳过回填（请检查 entrypoint 预迁移日志）")
        return

    try:
        _backfill_sort_order("requirements")
        db.expire_all()
        logger.info("requirements.sort_order 回填完成")
    except Exception:
        logger.exception("requirements.sort_order 回填失败，已跳过")


def migrate_testcase_sort_order(db: Session) -> None:
    """回填 testcases.sort_order。DDL 在 entrypoint 预迁移阶段执行，避免与 SQLAlchemy 连接争锁。"""
    if "testcases" not in inspect(engine).get_table_names():
        return
    if "sort_order" not in _testcase_columns():
        logger.warning("testcases.sort_order 列不存在，跳过回填（请检查 entrypoint 预迁移日志）")
        return

    try:
        _backfill_sort_order("testcases")
        db.expire_all()
        logger.info("testcases.sort_order 回填完成")
    except Exception:
        logger.exception("testcases.sort_order 回填失败，已跳过")


def migrate_department_permissions(db: Session) -> None:
    from app.models.department import Department
    from app.models.user import User

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    statements = []
    if "departments" not in table_names:
        dialect = engine.dialect.name
        id_column = (
            "id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY"
            if dialect == "mysql"
            else "id INTEGER PRIMARY KEY"
        )
        statements.append(
            "CREATE TABLE IF NOT EXISTS departments ("
            f"{id_column}, "
            "name VARCHAR(100) NOT NULL UNIQUE, "
            "description TEXT, "
            "created_at DATETIME, "
            "updated_at DATETIME)"
        )

    if "users" in table_names:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "department_id" not in user_columns:
            statements.append("ALTER TABLE users ADD COLUMN department_id INTEGER")

    if "projects" in table_names:
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "department_id" not in project_columns:
            statements.append("ALTER TABLE projects ADD COLUMN department_id INTEGER")

    if statements:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
        db.expire_all()

    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("users")} if "users" in table_names else set()
    project_columns = (
        {column["name"] for column in inspector.get_columns("projects")} if "projects" in table_names else set()
    )
    if "department_id" not in user_columns or "department_id" not in project_columns:
        logger = logging.getLogger(__name__)
        logger.warning("部门字段迁移未完成，跳过默认部门回填")
        return

    default_department = db.query(Department).filter(Department.name == "默认部门").first()
    needs_commit = False
    if not default_department:
        default_department = Department(name="默认部门", description="系统默认部门，同部门用户共享项目数据")
        db.add(default_department)
        db.flush()
        needs_commit = True

    for user in db.query(User).filter(User.department_id.is_(None)).all():
        user.department_id = default_department.id
        needs_commit = True
    if "projects" in table_names and "department_id" in project_columns:
        updated = db.execute(
            text("UPDATE projects SET department_id = :dept_id WHERE department_id IS NULL"),
            {"dept_id": default_department.id},
        )
        if updated.rowcount:
            needs_commit = True
    if needs_commit:
        db.commit()


def migrate_testcase_created_by(db: Session) -> None:
    inspector = inspect(engine)
    if "testcases" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("testcases")}
    if "created_by_id" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE testcases ADD COLUMN created_by_id INTEGER"))


# 已下线的老「接口自动化」模块表（子表先于父表，保证带 FK 时可安全 DROP）
_LEGACY_API_AUTOMATION_TABLES = [
    "api_test_step_results",
    "api_scheduled_task_suites",
    "api_test_cases",
    "api_test_runs",
    "api_scheduled_tasks",
    "api_test_suites",
    "api_environments",
]


def drop_legacy_api_automation_tables(db: Session) -> None:
    """清除已下线老模块的 7 张遗留表及其数据（幂等：不存在则跳过）。"""
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    to_drop = [t for t in _LEGACY_API_AUTOMATION_TABLES if t in existing]
    if not to_drop:
        return
    with engine.begin() as conn:
        for table in to_drop:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
    logging.getLogger(__name__).info("已清除老接口自动化遗留表: %s", ", ".join(to_drop))

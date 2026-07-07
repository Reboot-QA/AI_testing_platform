from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

import json

from app.database import engine


def _boolean_default(dialect: str) -> str:
    if dialect == "mysql":
        return "TINYINT(1) NOT NULL DEFAULT 0"
    return "BOOLEAN NOT NULL DEFAULT 0"


def migrate_api_test_suite_tree(db: Session) -> None:
    inspector = inspect(engine)
    if "api_test_suites" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("api_test_suites")}
    dialect = engine.dialect.name
    boolean_type = _boolean_default(dialect)
    statements = []
    if "parent_id" not in columns:
        statements.append("ALTER TABLE api_test_suites ADD COLUMN parent_id INTEGER")
    if "is_folder" not in columns:
        statements.append(f"ALTER TABLE api_test_suites ADD COLUMN is_folder {boolean_type}")
    if "sort_order" not in columns:
        statements.append("ALTER TABLE api_test_suites ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")

    if statements:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))


def migrate_api_variable_stores(db: Session) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    statements = []
    if "api_environments" in table_names:
        env_columns = {column["name"] for column in inspector.get_columns("api_environments")}
        if "variables" not in env_columns:
            statements.append("ALTER TABLE api_environments ADD COLUMN variables TEXT")

    if "projects" in table_names:
        project_columns = {column["name"] for column in inspector.get_columns("projects")}
        if "api_global_variables" not in project_columns:
            statements.append("ALTER TABLE projects ADD COLUMN api_global_variables TEXT")

    if not statements:
        return

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def migrate_api_scheduled_task_suites(db: Session) -> None:
    from app.models.api_automation import ApiScheduledTask, ApiScheduledTaskSuite

    inspector = inspect(engine)
    if "api_scheduled_tasks" not in inspector.get_table_names():
        return

    task_columns = {column["name"] for column in inspector.get_columns("api_scheduled_tasks")}
    if "last_run_ids" not in task_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE api_scheduled_tasks ADD COLUMN last_run_ids TEXT"))

    if "api_scheduled_task_suites" not in inspector.get_table_names():
        return

    tasks = db.query(ApiScheduledTask).all()
    changed = False
    for task in tasks:
        existing = (
            db.query(ApiScheduledTaskSuite)
            .filter(ApiScheduledTaskSuite.task_id == task.id)
            .count()
        )
        if existing == 0 and task.suite_id:
            db.add(
                ApiScheduledTaskSuite(
                    task_id=task.id,
                    suite_id=task.suite_id,
                    sort_order=0,
                )
            )
            changed = True
        if not task.last_run_ids and task.last_run_id:
            task.last_run_ids = json.dumps([task.last_run_id])
            changed = True
    if changed:
        db.commit()


def migrate_requirement_created_by(db: Session) -> None:
    inspector = inspect(engine)
    if "requirements" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("requirements")}
    if "created_by_id" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE requirements ADD COLUMN created_by_id INTEGER"))


def migrate_testcase_created_by(db: Session) -> None:
    inspector = inspect(engine)
    if "testcases" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("testcases")}
    if "created_by_id" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE testcases ADD COLUMN created_by_id INTEGER"))

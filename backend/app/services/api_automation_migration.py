from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

import json
import logging

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


def migrate_department_permissions(db: Session) -> None:
    from app.models.department import Department
    from app.models.project import Project
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
    for project in db.query(Project).filter(Project.department_id.is_(None)).all():
        project.department_id = default_department.id
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

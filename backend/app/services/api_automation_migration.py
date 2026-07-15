import logging

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine


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

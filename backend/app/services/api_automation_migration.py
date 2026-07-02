from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

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

    if not statements:
        return

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))

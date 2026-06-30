from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine


def migrate_api_test_suite_tree(db: Session) -> None:
    inspector = inspect(engine)
    if "api_test_suites" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("api_test_suites")}
    statements = []
    if "parent_id" not in columns:
        statements.append("ALTER TABLE api_test_suites ADD COLUMN parent_id INTEGER")
    if "is_folder" not in columns:
        statements.append("ALTER TABLE api_test_suites ADD COLUMN is_folder BOOLEAN NOT NULL DEFAULT 0")
    if "sort_order" not in columns:
        statements.append("ALTER TABLE api_test_suites ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")

    if not statements:
        return

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))

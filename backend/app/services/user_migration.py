from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.database import engine


def migrate_user_must_change_password(db: Session) -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "must_change_password" in user_columns:
        return
    dialect = engine.dialect.name
    if dialect == "mysql":
        statement = "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"
    else:
        statement = "ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0"
    with engine.begin() as conn:
        conn.execute(text(statement))
    db.expire_all()


def migrate_user_optional_email() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    email_col = next((col for col in inspector.get_columns("users") if col["name"] == "email"), None)
    if not email_col or email_col.get("nullable"):
        return

    dialect = engine.dialect.name
    if dialect == "mysql":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users MODIFY email VARCHAR(100) NULL"))
        return

    if dialect != "sqlite":
        return

    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.execute(
            text(
                """
                CREATE TABLE users_new (
                    id INTEGER NOT NULL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    email VARCHAR(100),
                    hashed_password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(100),
                    role VARCHAR(20) NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO users_new (
                    id, username, email, hashed_password, full_name, role, is_active, created_at
                )
                SELECT
                    id,
                    username,
                    NULLIF(TRIM(email), ''),
                    hashed_password,
                    full_name,
                    role,
                    is_active,
                    created_at
                FROM users
                """
            )
        )
        conn.execute(text("DROP TABLE users"))
        conn.execute(text("ALTER TABLE users_new RENAME TO users"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)"))
        conn.execute(text("PRAGMA foreign_keys=ON"))

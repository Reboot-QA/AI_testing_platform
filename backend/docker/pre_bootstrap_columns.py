"""Docker 启动前幂等补列，避免 bootstrap / 业务查询因缺列返回 500。"""

from __future__ import annotations

import os
import sys
import time

import pymysql

# (表名, 列名, DDL)；表不存在时跳过（由 create_all 首次建表）
COLUMN_SPECS: list[tuple[str, str, str]] = [
    ("requirements", "sort_order", "ALTER TABLE requirements ADD COLUMN sort_order INT NOT NULL DEFAULT 0"),
    ("testcases", "sort_order", "ALTER TABLE testcases ADD COLUMN sort_order INT NOT NULL DEFAULT 0"),
    ("projects", "owner_seq", "ALTER TABLE projects ADD COLUMN owner_seq INTEGER NULL"),
    (
        "projects",
        "last_import_url",
        "ALTER TABLE projects ADD COLUMN last_import_url VARCHAR(1000) NULL",
    ),
    ("project_members", "created_by", "ALTER TABLE project_members ADD COLUMN created_by INTEGER NULL"),
    ("project_members", "created_at", "ALTER TABLE project_members ADD COLUMN created_at DATETIME NULL"),
    ("apifox_folders", "kind", "ALTER TABLE apifox_folders ADD COLUMN kind VARCHAR(20) NOT NULL DEFAULT 'endpoint'"),
    (
        "apifox_endpoints",
        "server_name",
        "ALTER TABLE apifox_endpoints ADD COLUMN server_name VARCHAR(100)",
    ),
    (
        "apifox_endpoints",
        "response_schema_id",
        "ALTER TABLE apifox_endpoints ADD COLUMN response_schema_id INTEGER",
    ),
    (
        "apifox_endpoints",
        "contract_strict",
        "ALTER TABLE apifox_endpoints ADD COLUMN contract_strict BOOLEAN NOT NULL DEFAULT 0",
    ),
    ("apifox_endpoints", "pre_processors", "ALTER TABLE apifox_endpoints ADD COLUMN pre_processors TEXT"),
    ("apifox_endpoints", "post_processors", "ALTER TABLE apifox_endpoints ADD COLUMN post_processors TEXT"),
    (
        "apifox_endpoints",
        "version",
        "ALTER TABLE apifox_endpoints ADD COLUMN version INTEGER NOT NULL DEFAULT 1",
    ),
    (
        "apifox_endpoints",
        "cases_stale",
        "ALTER TABLE apifox_endpoints ADD COLUMN cases_stale BOOLEAN NOT NULL DEFAULT 0",
    ),
    ("apifox_endpoints", "deleted_at", "ALTER TABLE apifox_endpoints ADD COLUMN deleted_at DATETIME"),
    ("apifox_endpoints", "deleted_by", "ALTER TABLE apifox_endpoints ADD COLUMN deleted_by INTEGER"),
    (
        "apifox_schemas",
        "version",
        "ALTER TABLE apifox_schemas ADD COLUMN version INTEGER NOT NULL DEFAULT 1",
    ),
    (
        "apifox_scripts",
        "version",
        "ALTER TABLE apifox_scripts ADD COLUMN version INTEGER NOT NULL DEFAULT 1",
    ),
    (
        "apifox_endpoint_cases",
        "version",
        "ALTER TABLE apifox_endpoint_cases ADD COLUMN version INTEGER NOT NULL DEFAULT 1",
    ),
    (
        "apifox_endpoint_cases",
        "category",
        "ALTER TABLE apifox_endpoint_cases ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT 'other'",
    ),
    ("apifox_endpoint_cases", "deleted_at", "ALTER TABLE apifox_endpoint_cases ADD COLUMN deleted_at DATETIME"),
    ("apifox_endpoint_cases", "deleted_by", "ALTER TABLE apifox_endpoint_cases ADD COLUMN deleted_by INTEGER"),
    (
        "apifox_scenarios",
        "version",
        "ALTER TABLE apifox_scenarios ADD COLUMN version INTEGER NOT NULL DEFAULT 1",
    ),
    ("apifox_scenarios", "deleted_at", "ALTER TABLE apifox_scenarios ADD COLUMN deleted_at DATETIME"),
    ("apifox_scenarios", "deleted_by", "ALTER TABLE apifox_scenarios ADD COLUMN deleted_by INTEGER"),
    (
        "apifox_suites",
        "version",
        "ALTER TABLE apifox_suites ADD COLUMN version INTEGER NOT NULL DEFAULT 1",
    ),
    ("apifox_suites", "deleted_at", "ALTER TABLE apifox_suites ADD COLUMN deleted_at DATETIME"),
    ("apifox_suites", "deleted_by", "ALTER TABLE apifox_suites ADD COLUMN deleted_by INTEGER"),
]


def _connect():
    return pymysql.connect(
        host=os.environ.get("DB_HOST", "mysql"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "ai_testcase"),
        charset="utf8mb4",
        connect_timeout=5,
        autocommit=True,
    )


def _table_exists(cur, database: str, table: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
        LIMIT 1
        """,
        (database, table),
    )
    return cur.fetchone() is not None


def _column_exists(cur, database: str, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (database, table, column),
    )
    return cur.fetchone() is not None


def ensure_column(cur, database: str, table: str, column: str, ddl: str) -> bool:
    if not _table_exists(cur, database, table):
        print(f"[SKIP] table {table} not found")
        return True
    if _column_exists(cur, database, table, column):
        print(f"[OK] {table}.{column} already exists")
        return True

    last_exc: Exception | None = None
    for attempt in range(1, 11):
        try:
            cur.execute("SET SESSION lock_wait_timeout = 10")
            cur.execute("SET SESSION innodb_lock_wait_timeout = 10")
            cur.execute(ddl)
            print(f"[OK] {table}.{column} column added")
            return True
        except pymysql.err.OperationalError as exc:
            code = exc.args[0] if exc.args else None
            if code == 1060:
                print(f"[OK] {table}.{column} already exists")
                return True
            last_exc = exc
            print(f"[WARN] {table}.{column} DDL retry {attempt}/10: {exc}", file=sys.stderr)
        except Exception as exc:
            last_exc = exc
            print(f"[WARN] {table}.{column} DDL retry {attempt}/10: {exc}", file=sys.stderr)
        if attempt < 10:
            time.sleep(3)

    print(f"[ERR] {table}.{column} 列添加失败: {last_exc}", file=sys.stderr)
    return False


def main() -> int:
    database = os.environ.get("DB_NAME", "ai_testcase")
    conn = None
    failed = 0
    try:
        conn = _connect()
        with conn.cursor() as cur:
            for table, column, ddl in COLUMN_SPECS:
                if not ensure_column(cur, database, table, column, ddl):
                    failed += 1
    except Exception as exc:
        print(f"[ERR] pre-bootstrap columns failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            conn.close()

    if failed:
        print(f"[ERR] {failed} 个列补全失败", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

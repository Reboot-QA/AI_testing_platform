"""Apifox 环境数据库连接 · 业务层（CRUD；密码只写不回显）。

非法输入抛 ValueError（router 转 400）。写操作末尾 commit。权限在 router。
"""

from typing import List

from sqlalchemy.orm import Session

from app.models.apifox.database_conn import ApifoxEnvironmentDatabase
from app.repositories.apifox import database_conn_repo as repo
from app.routers.apifox.database_schemas import DatabaseCreate, DatabaseOut, DatabaseUpdate

VALID_DB_TYPES = {"mysql"}


def _validate_type(db_type: str) -> None:
    if db_type not in VALID_DB_TYPES:
        raise ValueError("暂仅支持 mysql 数据库连接")


def _out(conn: ApifoxEnvironmentDatabase) -> DatabaseOut:
    return DatabaseOut(
        id=conn.id,
        environment_id=conn.environment_id,
        name=conn.name,
        db_type=conn.db_type,
        host=conn.host,
        port=conn.port,
        username=conn.username,
        database=conn.database,
        has_password=bool(conn.password),
        sort_order=conn.sort_order,
    )


def list_databases(db: Session, environment_id: int) -> List[DatabaseOut]:
    return [_out(c) for c in repo.list_by_environment(db, environment_id)]


def create_database(db: Session, environment_id: int, data: DatabaseCreate) -> DatabaseOut:
    _validate_type(data.db_type)
    conn = ApifoxEnvironmentDatabase(
        environment_id=environment_id,
        name=data.name,
        db_type=data.db_type,
        host=data.host,
        port=data.port,
        username=data.username,
        password=data.password,
        database=data.database,
    )
    repo.add(db, conn)
    db.commit()
    db.refresh(conn)
    return _out(conn)


def update_database(db: Session, conn: ApifoxEnvironmentDatabase, data: DatabaseUpdate) -> DatabaseOut:
    if data.db_type is not None:
        _validate_type(data.db_type)
        conn.db_type = data.db_type
    if data.name is not None:
        conn.name = data.name
    if data.host is not None:
        conn.host = data.host
    if data.port is not None:
        conn.port = data.port
    if data.username is not None:
        conn.username = data.username
    if data.password is not None:  # None=保持原密码；空串=清空
        conn.password = data.password
    if data.database is not None:
        conn.database = data.database
    if data.sort_order is not None:
        conn.sort_order = data.sort_order
    db.commit()
    db.refresh(conn)
    return _out(conn)


def delete_database(db: Session, conn: ApifoxEnvironmentDatabase) -> None:
    repo.delete(db, conn)
    db.commit()

"""环境数据库连接 · CRUD + 密码只写不回显 + 密码更新语义。

被测：app/services/apifox/database_conn_service.py。
"""

import pytest

from app.models.apifox.variable import ApifoxEnvironment
from app.repositories.apifox import database_conn_repo
from app.routers.apifox.database_schemas import DatabaseCreate, DatabaseUpdate
from app.services.apifox import database_conn_service as svc


def _env(db, project_id=1):
    e = ApifoxEnvironment(project_id=project_id, name="dev")
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def test_create_exposes_has_password_not_plaintext(db):
    env = _env(db)

    out = svc.create_database(
        db, env.id, DatabaseCreate(name="c", host="h", username="u", password="secret", database="d")
    )

    assert out.has_password is True
    assert not hasattr(out, "password")  # Out 契约不含 password 字段


def test_create_without_password_has_password_false(db):
    env = _env(db)

    out = svc.create_database(db, env.id, DatabaseCreate(name="c"))

    assert out.has_password is False


def test_invalid_db_type_rejected(db):
    env = _env(db)

    with pytest.raises(ValueError, match="mysql"):
        svc.create_database(db, env.id, DatabaseCreate(name="c", db_type="oracle"))


def test_update_password_none_keeps_existing(db):
    env = _env(db)
    out = svc.create_database(db, env.id, DatabaseCreate(name="c", password="p1"))

    svc.update_database(db, database_conn_repo.get(db, out.id), DatabaseUpdate(host="h2"))

    conn = database_conn_repo.get(db, out.id)
    assert conn.password == "p1"  # 未传 password → 保持
    assert conn.host == "h2"


def test_update_password_empty_clears(db):
    env = _env(db)
    out = svc.create_database(db, env.id, DatabaseCreate(name="c", password="p1"))

    svc.update_database(db, database_conn_repo.get(db, out.id), DatabaseUpdate(password=""))

    assert database_conn_repo.get(db, out.id).password == ""


def test_list_and_delete(db):
    env = _env(db)
    out = svc.create_database(db, env.id, DatabaseCreate(name="c"))

    assert len(svc.list_databases(db, env.id)) == 1

    svc.delete_database(db, database_conn_repo.get(db, out.id))
    assert svc.list_databases(db, env.id) == []

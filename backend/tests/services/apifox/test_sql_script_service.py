"""Apifox SQL 脚本库 · CRUD / 唯一名 / 乐观锁 / 被引用删除拦截。"""

import json

import pytest

from app.repositories.apifox import sql_script_repo
from app.routers.apifox.sql_script_schemas import SqlScriptCreate, SqlScriptUpdate
from app.services.apifox import sql_script_service as svc
from app.services.apifox.errors import ConflictError


def _create(db, name="查用户", content="SELECT 1"):
    return svc.create_script(db, 1, SqlScriptCreate(name=name, content=content))


def test_create_and_list(db):
    out = _create(db)

    assert out.id and out.version == 1 and out.content == "SELECT 1"
    briefs = svc.list_scripts(db, 1)
    assert [b.name for b in briefs] == ["查用户"]


def test_create_duplicate_name_rejected(db):
    _create(db, name="dup")
    with pytest.raises(ValueError, match="已存在"):
        _create(db, name="dup")


def test_update_optimistic_conflict(db):
    out = _create(db)
    # 用过期 version 更新 → 409 ConflictError
    svc.update_script(db, sql_script_repo.get_script(db, out.id), SqlScriptUpdate(content="SELECT 2", expected_version=1))
    with pytest.raises(ConflictError):
        svc.update_script(
            db, sql_script_repo.get_script(db, out.id), SqlScriptUpdate(content="SELECT 3", expected_version=1)
        )


def test_delete_blocked_when_referenced_by_case(db, make_case):
    out = _create(db)
    case = make_case(project_id=1)
    case.pre_processors = json.dumps([{"kind": "database_script", "sql_script_id": out.id}])
    db.commit()

    with pytest.raises(ValueError, match="引用"):
        svc.delete_script(db, sql_script_repo.get_script(db, out.id))


def test_delete_ok_when_not_referenced(db):
    out = _create(db)
    svc.delete_script(db, sql_script_repo.get_script(db, out.id))
    assert sql_script_repo.get_script(db, out.id) is None


def test_validate_processor_refs(db):
    out = _create(db)

    class _Row:
        def __init__(self, kind, sql_script_id=None):
            self.kind = kind
            self.sql_script_id = sql_script_id

    # 合法引用不抛
    svc.validate_processor_refs(db, 1, [_Row("database_script", out.id)])
    # 缺 id → 报错
    with pytest.raises(ValueError, match="未选择"):
        svc.validate_processor_refs(db, 1, [_Row("database_script", None)])
    # id 不存在 → 报错
    with pytest.raises(ValueError, match="不存在"):
        svc.validate_processor_refs(db, 1, [_Row("database_script", 99999)])

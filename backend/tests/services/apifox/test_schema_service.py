"""数据模型 · 引用计数 + 删除/改名保护 + 环检测 + 未知/自引用校验。

被测：app/services/apifox/schema_service.py。仅业务逻辑，sqlite 隔离库。
"""

import json

import pytest

from app.models.apifox.endpoint import ApifoxEndpoint
from app.repositories.apifox import schema_repo
from app.routers.apifox.data_model_schemas import SchemaCreate, SchemaUpdate
from app.services.apifox import schema_service as svc

_OBJ = '{"type":"object","properties":{}}'


def _create(db, name, json_schema=_OBJ, project_id=1):
    return svc.create_schema(db, project_id, SchemaCreate(name=name, json_schema=json_schema))


def _ref_obj(field, model_name):
    return f'{{"type":"object","properties":{{"{field}":{{"$ref":"#/models/{model_name}"}}}}}}'


def _get(db, name, project_id=1):
    return schema_repo.get_schema_by_name(db, project_id, name)


def _bind_endpoint(db, schema_id, project_id=1):
    ep = ApifoxEndpoint(
        project_id=project_id, name="ep", method="GET", path="/x", response_schema_id=schema_id
    )
    db.add(ep)
    db.commit()


def test_create_unknown_ref_rejected(db):
    with pytest.raises(ValueError, match="引用的数据模型不存在"):
        _create(db, "Order", _ref_obj("u", "User"))


def test_create_self_ref_rejected(db):
    with pytest.raises(ValueError, match="不能引用自身"):
        _create(db, "Node", _ref_obj("next", "Node"))


def test_create_valid_ref_inlines_resolved(db):
    _create(db, "User", '{"type":"object","properties":{"id":{"type":"integer"}}}')

    out = _create(db, "Order", _ref_obj("u", "User"))

    resolved = json.loads(out.resolved_schema)
    assert resolved["properties"]["u"]["properties"]["id"] == {"type": "integer"}


def test_update_forming_cycle_rejected(db):
    _create(db, "A")
    _create(db, "B", _ref_obj("a", "A"))
    a = _get(db, "A")

    with pytest.raises(ValueError, match="循环"):
        svc.update_schema(db, a, SchemaUpdate(json_schema=_ref_obj("b", "B")))


def test_rename_referenced_model_rejected(db):
    _create(db, "User")
    _create(db, "Order", _ref_obj("u", "User"))
    user = _get(db, "User")

    with pytest.raises(ValueError, match="改名"):
        svc.update_schema(db, user, SchemaUpdate(name="Account"))


def test_rename_unreferenced_model_ok(db):
    _create(db, "User")
    user = _get(db, "User")

    out = svc.update_schema(db, user, SchemaUpdate(name="Account"))

    assert out.name == "Account"


def test_delete_referenced_by_model_rejected(db):
    _create(db, "User")
    _create(db, "Order", _ref_obj("u", "User"))
    user = _get(db, "User")

    with pytest.raises(ValueError, match="其他模型"):
        svc.delete_schema(db, user)


def test_delete_referenced_by_endpoint_rejected(db):
    resp = _create(db, "Resp")
    _bind_endpoint(db, resp.id)
    schema = _get(db, "Resp")

    with pytest.raises(ValueError, match="接口"):
        svc.delete_schema(db, schema)


def test_delete_unreferenced_ok(db):
    _create(db, "Free")

    svc.delete_schema(db, _get(db, "Free"))

    assert _get(db, "Free") is None


def test_ref_count_combines_endpoint_and_model(db):
    _create(db, "User")
    _create(db, "Order", _ref_obj("u", "User"))
    user = _get(db, "User")
    _bind_endpoint(db, user.id)

    counts = {b.name: b.ref_count for b in svc.list_schemas(db, 1)}

    assert counts["User"] == 2  # 1 接口响应契约 + 1 模型 $ref
    assert counts["Order"] == 0

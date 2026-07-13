"""数据模型跨模型 $ref · 引用提取与递归内联解析。

被测：app/services/apifox/schema_ref.py。环/未知/超深均降级 {type:object}，不抛异常。
"""

import json

import pytest

from app.models.apifox.data_model import ApifoxSchema
from app.services.apifox import schema_ref


def _add(db, name, json_schema, project_id=1):
    s = ApifoxSchema(project_id=project_id, name=name, json_schema=json_schema)
    db.add(s)
    db.commit()
    return s


def _resolve(db, text, project_id=1):
    return json.loads(schema_ref.resolve_schema_text(db, project_id, text))


def test_extract_collects_nested_refs():
    text = ('{"type":"object","properties":{"u":{"$ref":"#/models/User"},'
            '"tags":{"type":"array","items":{"$ref":"#/models/Tag"}}}}')
    assert schema_ref.extract_model_refs(text) == {"User", "Tag"}


@pytest.mark.parametrize("text", ["{bad json", "", None])
def test_extract_bad_input_returns_empty(text):
    assert schema_ref.extract_model_refs(text) == set()


def test_extract_ignores_non_model_ref():
    text = '{"properties":{"x":{"$ref":"#/components/schemas/Foo"}}}'
    assert schema_ref.extract_model_refs(text) == set()


def test_resolve_inlines_single_ref(db):
    _add(db, "User", '{"type":"object","properties":{"id":{"type":"integer"}}}')

    resolved = _resolve(db, '{"type":"object","properties":{"u":{"$ref":"#/models/User"}}}')

    assert resolved["properties"]["u"] == {"type": "object", "properties": {"id": {"type": "integer"}}}


def test_resolve_inlines_multi_level(db):
    _add(db, "C", '{"type":"string"}')
    _add(db, "B", '{"type":"object","properties":{"c":{"$ref":"#/models/C"}}}')

    resolved = _resolve(db, '{"type":"object","properties":{"b":{"$ref":"#/models/B"}}}')

    assert resolved["properties"]["b"]["properties"]["c"] == {"type": "string"}


def test_resolve_cycle_degrades(db):
    _add(db, "A", '{"type":"object","properties":{"b":{"$ref":"#/models/B"}}}')
    _add(db, "B", '{"type":"object","properties":{"a":{"$ref":"#/models/A"}}}')

    resolved = _resolve(db, '{"$ref":"#/models/A"}')

    # A→B→A 成环，最内层 A 降级为 {type:object}
    assert resolved["properties"]["b"]["properties"]["a"] == {"type": "object"}


def test_resolve_unknown_ref_degrades(db):
    assert _resolve(db, '{"$ref":"#/models/Ghost"}') == {"type": "object"}


def test_resolve_no_ref_structurally_equal(db):
    text = '{"type":"object","properties":{"id":{"type":"integer"}}}'

    assert _resolve(db, text) == json.loads(text)


def test_resolve_depth_guard_degrades(db, monkeypatch):
    monkeypatch.setattr(schema_ref, "_MAX_REF_DEPTH", 1)
    _add(db, "C", '{"type":"string"}')
    _add(db, "B", '{"type":"object","properties":{"c":{"$ref":"#/models/C"}}}')
    _add(db, "A", '{"type":"object","properties":{"b":{"$ref":"#/models/B"}}}')

    resolved = _resolve(db, '{"$ref":"#/models/A"}')

    # A 内联(depth1)，B 超过 _MAX_REF_DEPTH=1 → 降级
    assert resolved["properties"]["b"] == {"type": "object"}

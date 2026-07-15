"""KvRow.type 契约 · 参数类型标注（Params 用）dump/load 保持，legacy JSON 缺省回退 string。"""

from app.routers.apifox.schemas import KvRow, RequestSpec


def test_kvrow_type_default_is_string_when_absent():
    row = KvRow(key="page", value="1")

    assert row.type == "string"


def test_kvrow_type_survives_dump_load_round_trip():
    spec = RequestSpec(query=[KvRow(key="page", value="1", type="integer")])

    reloaded = RequestSpec.model_validate_json(spec.model_dump_json())

    assert reloaded.query[0].type == "integer"


def test_legacy_spec_without_type_falls_back_to_string():
    legacy_json = '{"query": [{"key": "page", "value": "1"}]}'

    reloaded = RequestSpec.model_validate_json(legacy_json)

    assert reloaded.query[0].type == "string"

"""AI 生成接口测试用例 · service 单测。

覆盖：接口上下文构造、LLM 响应解析（含代码块/内嵌/畸形）、用例构造（参数填值/断言映射/
容错）、mock 模式分派。纯逻辑为主，不触网、不落库。
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.routers.apifox.case_schemas import AiGenCategory
from app.routers.apifox.schemas import BodySpec, KvRow, RequestSpec
from app.services.apifox import ai_case_service as svc


def _spec(**kw) -> RequestSpec:
    return RequestSpec(**kw)


def _endpoint(method="GET", path="/users", name="用户列表", desc=None, request_spec="{}"):
    return SimpleNamespace(
        method=method, path=path, name=name, description=desc,
        request_spec=request_spec, response_schema_id=None,
    )


# ---------- 上下文构造 ----------
def test_context_includes_method_and_path():
    ctx = svc.build_endpoint_context(_endpoint(method="POST", path="/orders"), _spec(), None)

    assert "POST /orders" in ctx


def test_context_marks_required_query_param():
    spec = _spec(query=[KvRow(key="page", type="integer", enabled=True, desc="页码")])

    ctx = svc.build_endpoint_context(_endpoint(), spec, None)

    assert "page" in ctx and "必填" in ctx


def test_context_includes_response_schema_when_present():
    ctx = svc.build_endpoint_context(_endpoint(), _spec(), '{"type":"object"}')

    assert "响应模型" in ctx and '"type":"object"' in ctx


# ---------- 响应解析 ----------
@pytest.mark.parametrize(
    "content",
    [
        '{"cases":[{"name":"a"}]}',
        '```json\n{"cases":[{"name":"a"}]}\n```',
        '好的，结果如下：{"cases":[{"name":"a"}]} 完成',
    ],
)
def test_parse_extracts_cases_list(content):
    cases = svc._parse_cases_payload(content)

    assert cases == [{"name": "a"}]


def test_parse_top_level_array():
    cases = svc._parse_cases_payload('[{"name":"a"},{"name":"b"}]')

    assert cases == [{"name": "a"}, {"name": "b"}]


def test_parse_filters_non_dict_elements():
    cases = svc._parse_cases_payload('{"cases":[{"name":"a"},"垃圾",123]}')

    assert cases == [{"name": "a"}]


def test_parse_malformed_raises():
    with pytest.raises(ValueError):
        svc._parse_cases_payload("这不是 JSON")


# ---------- 参数填值 ----------
def test_apply_kv_overrides_existing_key():
    rows = [KvRow(key="page", value="", enabled=False)]

    svc._apply_kv(rows, {"page": 3})

    assert rows[0].value == "3" and rows[0].enabled is True


def test_apply_kv_appends_new_key():
    rows = [KvRow(key="page", value="1")]

    svc._apply_kv(rows, {"size": 10})

    assert [r.key for r in rows] == ["page", "size"]
    assert rows[1].value == "10" and rows[1].enabled is True


# ---------- 断言映射 ----------
def test_assertion_invalid_type_dropped():
    assert svc._build_assertion({"type": "bogus"}) is None


def test_assertion_invalid_operator_falls_back_to_eq():
    row = svc._build_assertion({"type": "status_code", "operator": "??", "expected": 200})

    assert row is not None and row.operator == "eq"


def test_assertion_expected_coerced_to_str():
    row = svc._build_assertion({"type": "status_code", "expected": 400})

    assert row is not None and row.expected == "400"


# ---------- 用例构造 ----------
def test_build_case_fills_base_spec_value():
    base = _spec(query=[KvRow(key="page", value="", enabled=False)])

    case = svc._build_case(base, {"name": "正常查询", "category": "positive", "query": {"page": 2}})

    assert case is not None
    assert case.request_spec.query[0].value == "2"
    assert base.query[0].value == ""  # 深拷贝：不污染原 spec


def test_build_case_serializes_json_body():
    base = _spec(body=BodySpec(type="json"))

    case = svc._build_case(base, {"name": "创建", "body": {"title": "x"}})

    assert case is not None and case.request_spec.body.raw == '{"title": "x"}'


def test_build_case_fills_form_body():
    base = _spec(body=BodySpec(type="form-data", form=[KvRow(key="file", value="")]))

    case = svc._build_case(base, {"name": "表单", "body": {"file": "a.txt", "tag": "x"}})

    assert case is not None
    form = {r.key: r.value for r in case.request_spec.body.form}
    assert form == {"file": "a.txt", "tag": "x"}


def test_build_case_non_dict_item_returns_none():
    assert svc._build_case(_spec(), "垃圾") is None
    assert svc._build_case(_spec(), 123) is None


def test_build_case_maps_assertions():
    case = svc._build_case(
        _spec(),
        {"name": "n", "assertions": [{"type": "status_code", "operator": "eq", "expected": 200}]},
    )

    assert case is not None
    assert [(a.type, a.expected) for a in case.assertions] == [("status_code", "200")]


def test_build_case_unknown_category_becomes_other():
    case = svc._build_case(_spec(), {"name": "n", "category": "weird"})

    assert case is not None and case.category == "other"


def test_build_case_empty_name_returns_none():
    assert svc._build_case(_spec(), {"name": "  ", "category": "positive"}) is None


def test_build_cases_skips_invalid_items():
    raw = [{"name": ""}, {"name": "有效", "category": "positive"}]

    cases = svc._build_cases(_spec(), raw)

    assert [c.name for c in cases] == ["有效"]


# ---------- mock 模式 ----------
def test_mock_cases_respects_category_counts():
    cats = [AiGenCategory(category="positive", count=1), AiGenCategory(category="negative", count=2)]

    cases = svc._mock_cases(_spec(), cats)

    assert len(cases) == 3
    assert [c.category for c in cases] == ["positive", "negative", "negative"]


def test_mock_positive_asserts_200_negative_asserts_400():
    cats = [AiGenCategory(category="positive", count=1), AiGenCategory(category="negative", count=1)]

    cases = svc._mock_cases(_spec(), cats)

    assert cases[0].assertions[0].expected == "200"
    assert cases[1].assertions[0].expected == "400"


def test_generate_cases_mock_mode_dispatches_without_network():
    llm_config = {"mock_mode": True, "api_key": "", "api_base": "", "model": ""}
    cats = [AiGenCategory(category="positive", count=2)]

    cases, mode = asyncio.run(svc.generate_cases(None, _endpoint(), cats, llm_config))

    assert mode == "mock" and len(cases) == 2

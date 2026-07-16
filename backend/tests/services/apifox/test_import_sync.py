"""更新 Swagger（增量同步）· diff 分类 + 引用检测 + apply 应用。

覆盖：新增/变更(参数/请求体)/移除识别、值编辑不误报、被场景/套件引用检测、
apply 建新增/只改契约保留本地/删无引用/保留并告警被引用、无效 openapi 异常。
"""

import pytest

from app.models.apifox.case import ApifoxCaseAssertion, ApifoxCaseExtract, ApifoxEndpointCase
from app.models.apifox.endpoint import (
    ApifoxEndpoint,
    ApifoxEndpointAssertion,
    ApifoxEndpointExtract,
)
from app.models.apifox.scenario import ApifoxScenario, ApifoxScenarioStep
from app.models.apifox.script import ApifoxCaseScript, ApifoxEndpointScript
from app.models.apifox.suite import ApifoxSuite, ApifoxSuiteItem
from app.routers.apifox.schemas import BodySpec, KvRow, RequestSpec
from app.services.apifox import import_sync_service as sync

PID = 1


# ---------- builders ----------
def _spec(query=(), cookies=(), body=None) -> str:
    return RequestSpec(
        query=[KvRow(key=k) if isinstance(k, str) else k for k in query],
        cookies=[KvRow(key=c) for c in cookies],
        body=body or BodySpec(),
    ).model_dump_json()


def _endpoint(db, method="GET", path="/x", name="ep", spec=None) -> ApifoxEndpoint:
    ep = ApifoxEndpoint(
        project_id=PID, name=name, method=method, path=path, request_spec=spec or _spec()
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return ep


def _case(db, ep, name="c") -> ApifoxEndpointCase:
    c = ApifoxEndpointCase(project_id=PID, endpoint_id=ep.id, name=name)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _ref_by_scenario(db, case, name="下单链路") -> None:
    scn = ApifoxScenario(project_id=PID, name=name)
    db.add(scn)
    db.commit()
    db.add(ApifoxScenarioStep(scenario_id=scn.id, type="case", ref_case_id=case.id))
    db.commit()


def _ref_by_suite(db, case, name="回归套件") -> None:
    suite = ApifoxSuite(project_id=PID, name=name)
    db.add(suite)
    db.commit()
    db.add(ApifoxSuiteItem(suite_id=suite.id, target_type="case", target_id=case.id))
    db.commit()


def _op(method="get", path="/x", query=(), json_body=False) -> dict:
    op = {
        "summary": f"{method.upper()} {path}",
        "parameters": [{"name": k, "in": "query", "schema": {"type": "string"}} for k in query],
        "responses": {"200": {"description": "ok"}},
    }
    if json_body:
        op["requestBody"] = {
            "content": {"application/json": {"schema": {"type": "object"}}}
        }
    return op


def _build_doc(specs) -> dict:
    """specs: list of dict(method, path, query?, json_body?) → 合法 openapi 文档。"""
    doc: dict = {"openapi": "3.0.0", "paths": {}}
    for s in specs:
        method = s["method"].lower()
        path = s["path"]
        doc["paths"].setdefault(path, {})[method] = _op(
            method=method, path=path, query=s.get("query", ()), json_body=s.get("json_body", False)
        )
    return doc


# ---------- compute_diff ----------
def test_diff_identifies_added(db):
    _endpoint(db, "GET", "/keep")

    diff = sync.compute_diff(db, PID, _build_doc([
        {"method": "GET", "path": "/keep"},
        {"method": "GET", "path": "/new"},
    ]))

    assert [e.path for e in diff.added] == ["/new"]
    assert diff.changed == [] and diff.removed == []


def test_diff_identifies_changed_query_param(db):
    _endpoint(db, "GET", "/users", spec=_spec(query=()))

    diff = sync.compute_diff(db, PID, _build_doc([
        {"method": "GET", "path": "/users", "query": ["page"]},
    ]))

    assert len(diff.changed) == 1
    assert "Query 参数" in diff.changed[0].changes


def test_diff_and_apply_detect_path_param_type_change(db):
    # 唯一差异是 path 参数类型（string→integer），键不变 → 仍须识别为「Path 参数」变更
    ep = _endpoint(
        db, "GET", "/users/{id}", spec=RequestSpec(path_params=[KvRow(key="id")]).model_dump_json()
    )
    doc = {
        "openapi": "3.0.0",
        "paths": {
            "/users/{id}": {
                "get": {
                    "summary": "GET /users/{id}",
                    "parameters": [
                        {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }

    diff = sync.compute_diff(db, PID, doc)
    assert len(diff.changed) == 1 and "Path 参数" in diff.changed[0].changes

    assert sync.apply_sync(db, PID, doc, False).updated == 1
    db.refresh(ep)
    assert RequestSpec.model_validate_json(ep.request_spec).path_params[0].type == "integer"


def test_diff_identifies_changed_body(db):
    _endpoint(db, "POST", "/users", spec=_spec())  # body none

    diff = sync.compute_diff(db, PID, _build_doc([
        {"method": "POST", "path": "/users", "json_body": True},
    ]))

    assert len(diff.changed) == 1
    assert "请求体" in diff.changed[0].changes


def test_diff_no_false_positive_on_value_edit(db):
    # 已有接口带用户编辑过的取值/说明，但键集不变 → 不应判为变更
    edited = KvRow(key="page", value="99", enabled=False, desc="本地备注")
    _endpoint(db, "GET", "/users", spec=_spec(query=[edited]))

    diff = sync.compute_diff(db, PID, _build_doc([
        {"method": "GET", "path": "/users", "query": ["page"]},
    ]))

    assert diff.changed == []


def test_diff_identifies_removed_unreferenced(db):
    _endpoint(db, "GET", "/keep")
    old = _endpoint(db, "GET", "/old")
    _case(db, old)  # 有用例但未被任何场景/套件引用

    diff = sync.compute_diff(db, PID, _build_doc([{"method": "GET", "path": "/keep"}]))

    assert len(diff.removed) == 1
    assert diff.removed[0].path == "/old"
    assert diff.removed[0].referenced is False
    assert diff.removed[0].case_count == 1


def test_diff_removed_referenced_by_scenario(db):
    _endpoint(db, "GET", "/keep")
    old = _endpoint(db, "GET", "/old")
    case = _case(db, old, name="老用例")
    _ref_by_scenario(db, case, name="下单链路")

    diff = sync.compute_diff(db, PID, _build_doc([{"method": "GET", "path": "/keep"}]))

    removed = diff.removed[0]
    assert removed.referenced is True
    assert removed.references[0].scenarios == ["下单链路"]


def test_diff_removed_referenced_by_suite(db):
    _endpoint(db, "GET", "/keep")
    old = _endpoint(db, "GET", "/old")
    case = _case(db, old)
    _ref_by_suite(db, case, name="回归套件")

    diff = sync.compute_diff(db, PID, _build_doc([{"method": "GET", "path": "/keep"}]))

    removed = diff.removed[0]
    assert removed.referenced is True
    assert removed.references[0].suites == ["回归套件"]


# ---------- apply_sync ----------
def test_apply_creates_added(db):
    report = sync.apply_sync(db, PID, _build_doc([{"method": "GET", "path": "/new"}]), False)

    assert report.added == 1
    assert db.query(ApifoxEndpoint).filter_by(project_id=PID, path="/new").count() == 1


def test_apply_updates_changed_preserves_local_and_cases(db):
    ep = _endpoint(db, "GET", "/users", spec=_spec(query=(), cookies=["sid"]))
    case = _case(db, ep, name="保留用例")
    original_case_spec = case.request_spec

    report = sync.apply_sync(
        db, PID, _build_doc([{"method": "GET", "path": "/users", "query": ["page"]}]), False
    )

    assert report.updated == 1
    db.refresh(ep)
    spec = RequestSpec.model_validate_json(ep.request_spec)
    assert [r.key for r in spec.query] == ["page"]  # 契约已同步
    assert [r.key for r in spec.cookies] == ["sid"]  # 本地 cookies 保留
    db.refresh(case)
    assert case.request_spec == original_case_spec  # 用例不动


def test_apply_deletes_unreferenced_when_flag_true(db):
    _endpoint(db, "GET", "/keep")
    old = _endpoint(db, "GET", "/old")
    case = _case(db, old)
    # 两级处理器子表：删除后不应留孤儿行
    db.add(ApifoxCaseAssertion(case_id=case.id, type="status_code"))
    db.add(ApifoxCaseExtract(case_id=case.id, var_name="token"))
    db.add(ApifoxCaseScript(case_id=case.id, script_id=1, phase="pre"))
    db.add(ApifoxEndpointAssertion(endpoint_id=old.id, type="status_code"))
    db.add(ApifoxEndpointExtract(endpoint_id=old.id, var_name="rid"))
    db.add(ApifoxEndpointScript(endpoint_id=old.id, script_id=1, phase="pre"))
    db.commit()

    report = sync.apply_sync(db, PID, _build_doc([{"method": "GET", "path": "/keep"}]), True)

    assert report.deleted == 1
    assert db.query(ApifoxEndpoint).filter_by(path="/old").count() == 0
    assert db.query(ApifoxEndpointCase).filter_by(endpoint_id=old.id).count() == 0
    assert db.query(ApifoxCaseAssertion).filter_by(case_id=case.id).count() == 0
    assert db.query(ApifoxCaseExtract).filter_by(case_id=case.id).count() == 0
    assert db.query(ApifoxCaseScript).filter_by(case_id=case.id).count() == 0
    assert db.query(ApifoxEndpointAssertion).filter_by(endpoint_id=old.id).count() == 0
    assert db.query(ApifoxEndpointExtract).filter_by(endpoint_id=old.id).count() == 0
    assert db.query(ApifoxEndpointScript).filter_by(endpoint_id=old.id).count() == 0


def test_apply_keeps_unreferenced_when_flag_false(db):
    _endpoint(db, "GET", "/keep")
    _endpoint(db, "GET", "/old")

    report = sync.apply_sync(db, PID, _build_doc([{"method": "GET", "path": "/keep"}]), False)

    assert report.deleted == 0
    assert db.query(ApifoxEndpoint).filter_by(path="/old").count() == 1


def test_apply_never_deletes_referenced_and_warns(db):
    _endpoint(db, "GET", "/keep")
    old = _endpoint(db, "GET", "/old")
    case = _case(db, old)
    _ref_by_scenario(db, case, name="下单链路")

    # 即使 delete_unreferenced=True，被引用的也绝不删
    report = sync.apply_sync(db, PID, _build_doc([{"method": "GET", "path": "/keep"}]), True)

    assert report.deleted == 0
    assert report.kept_referenced == 1
    assert report.warnings and "下单链路" in report.warnings[0]
    assert db.query(ApifoxEndpoint).filter_by(path="/old").count() == 1


@pytest.mark.parametrize("fn", [sync.compute_diff, lambda db, pid, doc: sync.apply_sync(db, pid, doc, False)])
def test_invalid_openapi_raises(db, fn):
    with pytest.raises(ValueError):
        fn(db, PID, {"paths": {}})  # 缺 openapi:3.x 声明

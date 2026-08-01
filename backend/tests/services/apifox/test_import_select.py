"""导入预览 & 按用户选择导入（替代「已有接口就强制走更新同步」）。

覆盖：预览按 tag 分组并标注已存在/契约变更、只导入勾选项、导入到指定目标目录、
已存在接口按 skip/overwrite 处理、目标目录非法、数据模型开关。
"""

import pytest

from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.data_model import ApifoxSchema
from app.models.apifox.endpoint import ApifoxEndpoint, ApifoxFolder
from app.routers.apifox.schemas import KvRow, RequestSpec
from app.services.apifox import import_service as svc

PID = 1


def _op(name, tag=None, query=()):
    op = {"summary": name, "responses": {}}
    if tag:
        op["tags"] = [tag]
    if query:
        op["parameters"] = [
            {"name": q, "in": "query", "schema": {"type": "string"}} for q in query
        ]
    return op


def _doc(paths, schemas=None, title="任务管理系统 API"):
    doc = {"openapi": "3.0.0", "info": {"title": title}, "paths": paths}
    if schemas:
        doc["components"] = {"schemas": {n: {"type": "object"} for n in schemas}}
    return doc


DOC = _doc(
    {
        "/auth/login": {"post": _op("用户登录", "认证")},
        "/auth/logout": {"post": _op("退出登录", "认证")},
        "/users": {"get": _op("用户列表", "用户")},
        "/ping": {"get": _op("心跳")},
    }
)


def _endpoint(db, method, path, query=(), folder_id=None) -> ApifoxEndpoint:
    ep = ApifoxEndpoint(
        project_id=PID,
        name=f"{method} {path}",
        method=method,
        path=path,
        folder_id=folder_id,
        request_spec=RequestSpec(query=[KvRow(key=q) for q in query]).model_dump_json(),
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return ep


def _folder(db, name, parent_id=None) -> ApifoxFolder:
    f = ApifoxFolder(project_id=PID, name=name, parent_id=parent_id)
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def _by_path(db, path) -> ApifoxEndpoint:
    return db.query(ApifoxEndpoint).filter_by(project_id=PID, path=path).one()


# ---------- 预览 ----------
def test_preview_groups_by_tag_and_keeps_untagged(db):
    out = svc.preview_openapi(db, PID, DOC)

    assert out["title"] == "任务管理系统 API"
    assert out["total"] == 4
    assert [(f["name"], len(f["endpoints"])) for f in out["folders"]] == [
        ("认证", 2),
        ("用户", 1),
        ("", 1),  # 无 tag 的接口单独一组，导入时落在目标目录本身
    ]
    assert out["folders"][0]["endpoints"][0]["key"] == "POST /auth/login"


def test_preview_marks_exists_and_changed(db):
    _endpoint(db, "POST", "/auth/login")  # 契约一致
    _endpoint(db, "GET", "/users", query=["keyword"])  # 库里多一个 query → 契约变更

    out = svc.preview_openapi(db, PID, _doc({
        "/auth/login": {"post": _op("用户登录", "认证")},
        "/users": {"get": _op("用户列表", "用户")},
        "/ping": {"get": _op("心跳")},
    }))
    flat = {e["key"]: e for f in out["folders"] for e in f["endpoints"]}

    assert (flat["POST /auth/login"]["exists"], flat["POST /auth/login"]["changed"]) == (True, False)
    assert (flat["GET /users"]["exists"], flat["GET /users"]["changed"]) == (True, True)
    assert (flat["GET /ping"]["exists"], flat["GET /ping"]["changed"]) == (False, False)
    assert (out["exists_count"], out["changed_count"]) == (2, 1)


def test_preview_counts_schemas_and_does_not_write(db):
    out = svc.preview_openapi(db, PID, _doc({"/x": {"get": _op("x")}}, schemas=["Task", "User"]))

    assert (out["schemas_total"], out["schemas_new"]) == (2, 2)
    assert db.query(ApifoxEndpoint).filter_by(project_id=PID).count() == 0
    assert db.query(ApifoxSchema).filter_by(project_id=PID).count() == 0


# ---------- 勾选项 ----------
def test_import_only_selected_keys(db):
    report = svc.import_openapi(
        db, PID, DOC, svc.ImportOptions(selected_keys={"POST /auth/login", "GET /ping"})
    )

    assert (report["total"], report["created"]) == (2, 2)
    assert {e.path for e in db.query(ApifoxEndpoint).filter_by(project_id=PID)} == {
        "/auth/login",
        "/ping",
    }


def test_import_without_selection_imports_all(db):
    report = svc.import_openapi(db, PID, DOC)

    assert report["created"] == 4


# ---------- 目标目录 ----------
def test_import_into_target_folder(db):
    target = _folder(db, "测试数据")

    svc.import_openapi(db, PID, DOC, svc.ImportOptions(target_folder_id=target.id))

    auth = db.query(ApifoxFolder).filter_by(project_id=PID, name="认证").one()
    assert auth.parent_id == target.id  # tag 目录建在目标目录下，而非根目录
    assert _by_path(db, "/auth/login").folder_id == auth.id
    assert _by_path(db, "/ping").folder_id == target.id  # 无 tag 的接口直接落在目标目录


def test_import_reuses_same_name_folder_under_target_only(db):
    target = _folder(db, "测试数据")
    _folder(db, "认证")  # 根目录下的同名目录不该被复用

    svc.import_openapi(db, PID, DOC, svc.ImportOptions(target_folder_id=target.id))

    assert db.query(ApifoxFolder).filter_by(project_id=PID, name="认证").count() == 2
    created = db.query(ApifoxFolder).filter_by(project_id=PID, name="认证", parent_id=target.id).one()
    assert _by_path(db, "/auth/login").folder_id == created.id


def test_import_rejects_foreign_target_folder(db):
    other = ApifoxFolder(project_id=PID + 1, name="别的项目目录")
    db.add(other)
    db.commit()

    with pytest.raises(ValueError):
        svc.import_openapi(db, PID, DOC, svc.ImportOptions(target_folder_id=other.id))


# ---------- 已存在接口的处理 ----------
def test_import_skips_existing_by_default(db):
    ep = _endpoint(db, "GET", "/users", query=["keyword"])

    report = svc.import_openapi(db, PID, _doc({"/users": {"get": _op("用户列表", "用户", ["page"])}}))

    assert (report["created"], report["updated"], report["skipped"]) == (0, 0, 1)
    assert "keyword" in ep.request_spec  # 未被覆盖


def test_import_overwrite_updates_contract_and_marks_cases_stale(db):
    ep = _endpoint(db, "GET", "/users", query=["keyword"])
    db.add(ApifoxEndpointCase(project_id=PID, endpoint_id=ep.id, name="正常查询"))
    db.commit()

    report = svc.import_openapi(
        db,
        PID,
        _doc({"/users": {"get": _op("用户列表", "用户", ["page"])}}),
        svc.ImportOptions(on_conflict="overwrite"),
    )

    assert (report["created"], report["updated"], report["skipped"]) == (0, 1, 0)
    spec = svc.load_spec(_by_path(db, "/users").request_spec)
    assert [r.key for r in spec.query] == ["page"]
    assert _by_path(db, "/users").cases_stale is True


def test_import_overwrite_skips_unchanged_contract(db):
    _endpoint(db, "GET", "/users")

    report = svc.import_openapi(
        db,
        PID,
        _doc({"/users": {"get": _op("用户列表", "用户")}}),
        svc.ImportOptions(on_conflict="overwrite"),
    )

    assert (report["updated"], report["skipped"]) == (0, 1)  # 契约没变就不算更新


def test_import_rejects_unknown_conflict_mode(db):
    with pytest.raises(ValueError):
        svc.import_openapi(db, PID, DOC, svc.ImportOptions(on_conflict="merge"))


# ---------- 数据模型开关 ----------
def test_import_can_skip_schemas(db):
    doc = _doc({"/x": {"get": _op("x")}}, schemas=["Task"])

    report = svc.import_openapi(db, PID, doc, svc.ImportOptions(with_schemas=False))

    assert report["schemas_created"] == 0
    assert db.query(ApifoxSchema).filter_by(project_id=PID).count() == 0

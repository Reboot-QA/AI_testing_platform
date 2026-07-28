"""apifox → OpenAPI 导出 + 上次导入 URL 记忆。"""

import json

from app.models.project import Project
from app.routers.apifox.imports import _remember_import_url
from app.services.apifox import export_service as svc


def test_build_openapi_has_info_and_paths(db, make_endpoint):
    make_endpoint(project_id=1, method="POST", path="/orders", name="下单")

    doc = svc.build_openapi(db, 1)

    assert doc["openapi"] == "3.0.0"
    assert "/orders" in doc["paths"]
    assert doc["paths"]["/orders"]["post"]["summary"] == "下单"
    assert doc["paths"]["/orders"]["post"]["responses"]["200"]


def test_build_openapi_maps_query_and_json_body(db, make_endpoint):
    ep = make_endpoint(project_id=1, method="POST", path="/x", name="x")
    ep.request_spec = json.dumps(
        {
            "query": [{"key": "page", "value": "1", "enabled": True, "type": "integer"}],
            "body": {"type": "json", "raw": '{"a":1}'},
        }
    )
    db.commit()

    op = svc.build_openapi(db, 1)["paths"]["/x"]["post"]

    assert any(p["name"] == "page" and p["in"] == "query" for p in op["parameters"])
    assert op["requestBody"]["content"]["application/json"]["example"] == {"a": 1}


def test_build_openapi_excludes_soft_deleted_endpoint(db, make_endpoint):
    from app.services.apifox import endpoint_service

    keep = make_endpoint(project_id=1, path="/keep", name="留")
    gone = make_endpoint(project_id=1, path="/gone", name="删")
    endpoint_service.delete_endpoint(db, endpoint_service.repo.get_endpoint(db, gone.id))

    paths = svc.build_openapi(db, 1)["paths"]

    assert "/keep" in paths and "/gone" not in paths
    assert keep  # 保活断言，避免未使用告警


def test_remember_import_url_trims_and_saves(db):
    p = Project(name="P", owner_id=1)
    db.add(p)
    db.commit()

    _remember_import_url(db, p.id, "  http://x/openapi.json ")

    db.refresh(p)
    assert p.last_import_url == "http://x/openapi.json"


def test_remember_import_url_ignores_empty(db):
    p = Project(name="P2", owner_id=1)
    db.add(p)
    db.commit()

    _remember_import_url(db, p.id, None)
    _remember_import_url(db, p.id, "   ")

    db.refresh(p)
    assert p.last_import_url is None


# ---------- 导出增强：范围/版本/格式 ----------
def test_export_yaml_and_json(db, make_endpoint):
    make_endpoint(project_id=1, method="GET", path="/x", name="x")
    jc, jm, jf = svc.export(db, 1, svc.ExportOptions(file_format="json"))
    yc, ym, yf = svc.export(db, 1, svc.ExportOptions(file_format="yaml"))
    assert jm == "application/json" and jf.endswith(".json") and '"openapi"' in jc
    assert ym == "application/yaml" and yf.endswith(".yaml") and "openapi:" in yc


def test_export_scope_endpoints_filters(db, make_endpoint):
    a = make_endpoint(project_id=1, path="/a", name="A")
    make_endpoint(project_id=1, path="/b", name="B")
    doc = svc.build_openapi(db, 1, svc.ExportOptions(scope="endpoints", endpoint_ids=[a.id]))
    assert "/a" in doc["paths"] and "/b" not in doc["paths"]


def test_export_spec_version_3_1(db, make_endpoint):
    make_endpoint(project_id=1, path="/x", name="x")
    doc = svc.build_openapi(db, 1, svc.ExportOptions(spec_version="3.1"))
    assert doc["openapi"] == "3.1.0"


def test_export_swagger2_structure(db, make_endpoint):
    make_endpoint(project_id=1, method="GET", path="/x", name="x")
    doc = svc.build_swagger2(db, 1)
    assert doc["swagger"] == "2.0" and "/x" in doc["paths"]
    assert "openapi" not in doc

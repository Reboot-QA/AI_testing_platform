"""apifox → Postman / 接口文档（HTML/Markdown/Word）导出。"""

import json

from app.services.apifox import export_docs, export_postman
from app.services.apifox.export_service import ExportOptions


def _spec_endpoint(make_endpoint, db):
    ep = make_endpoint(project_id=1, method="POST", path="/orders", name="下单")
    ep.request_spec = json.dumps(
        {
            "query": [{"key": "ref", "value": "web", "enabled": True, "type": "string"}],
            "headers": [{"key": "X-Token", "value": "t", "enabled": True}],
            "body": {"type": "json", "raw": '{"sku":"a"}'},
        }
    )
    db.commit()
    return ep


# ---------- Postman ----------
def test_export_postman_structure(db, make_endpoint):
    _spec_endpoint(make_endpoint, db)

    doc = export_postman.build_postman(db, 1)

    assert doc["info"]["schema"].endswith("collection.json")
    req = doc["item"][0]["request"]
    assert req["method"] == "POST"
    assert any(h["key"] == "X-Token" for h in req["header"])
    assert any(q["key"] == "ref" for q in req["url"]["query"])
    assert req["body"]["mode"] == "raw" and req["body"]["raw"] == '{"sku":"a"}'


def test_export_postman_scope_filter(db, make_endpoint):
    a = make_endpoint(project_id=1, path="/a", name="A")
    make_endpoint(project_id=1, path="/b", name="B")

    doc = export_postman.build_postman(db, 1, ExportOptions(scope="endpoints", endpoint_ids=[a.id]))

    names = json.dumps(doc, ensure_ascii=False)
    assert "/a" in names and "/b" not in names


# ---------- 文档 ----------
def test_export_markdown_contains_api(db, make_endpoint):
    _spec_endpoint(make_endpoint, db)

    md = export_docs.build_markdown(db, 1, ExportOptions())

    assert "### 下单" in md
    assert "`POST` `/orders`" in md
    assert "| ref | Query |" in md


def test_export_html_escapes_and_renders(db, make_endpoint):
    _spec_endpoint(make_endpoint, db)

    html = export_docs.build_html(db, 1, ExportOptions())

    assert "<!DOCTYPE html>" in html
    assert "/orders" in html and "X-Token" in html


def test_export_doc_word_returns_docx_bytes(db, make_endpoint):
    _spec_endpoint(make_endpoint, db)

    content, media, filename = export_docs.export_doc(db, 1, "word", ExportOptions())

    assert isinstance(content, bytes)
    assert content[:2] == b"PK"  # docx 即 zip
    assert filename.endswith(".docx")
    assert "wordprocessingml" in media


def test_export_doc_defaults_to_html(db, make_endpoint):
    make_endpoint(project_id=1, path="/x", name="x")

    content, media, filename = export_docs.export_doc(db, 1, "unknown")

    assert filename.endswith(".html") and "text/html" in media
    assert isinstance(content, str)

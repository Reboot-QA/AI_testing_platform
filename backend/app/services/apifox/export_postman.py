"""Apifox → Postman Collection v2.1 导出。

复用 export_service 的范围过滤（_collect）与 spec 解析（_spec/_rows），
按文件夹分组为 Postman folder → request 结构。
"""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.apifox.export_service import ExportOptions, _collect, _rows, _spec

_POSTMAN_SCHEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"


def _kv_rows(rows: Optional[List[dict]]) -> List[Dict[str, str]]:
    return [{"key": str(r.get("key")).strip(), "value": str(r.get("value") or "")} for r in _rows(rows)]


def _url(path: str, query: Optional[List[dict]]) -> Dict[str, Any]:
    segs = [s for s in (path or "/").split("/") if s]
    url: Dict[str, Any] = {"raw": path or "/", "path": segs}
    q = _kv_rows(query)
    if q:
        url["query"] = q
    return url


def _body(spec: dict) -> Optional[Dict[str, Any]]:
    body = spec.get("body") or {}
    btype = str(body.get("type") or "none")
    if btype in ("json", "raw", "xml"):
        raw = str(body.get("raw") or "")
        if not raw:
            return None
        out: Dict[str, Any] = {"mode": "raw", "raw": raw}
        if btype == "json":
            out["options"] = {"raw": {"language": "json"}}
        return out
    if btype == "form-data":
        return {"mode": "formdata", "formdata": _kv_rows(body.get("form"))}
    if btype == "urlencoded":
        return {"mode": "urlencoded", "urlencoded": _kv_rows(body.get("form"))}
    return None


def build_postman(db: Session, project_id: int, opts: Optional[ExportOptions] = None) -> Dict[str, Any]:
    opts = opts or ExportOptions()
    proj, endpoints, folders, _ = _collect(db, project_id, opts)

    groups: Dict[Optional[str], List[Dict[str, Any]]] = {}
    for ep in endpoints:
        spec = _spec(ep)
        request: Dict[str, Any] = {
            "method": ep.method.upper(),
            "header": _kv_rows(spec.get("headers")),
            "url": _url(ep.path or "/", spec.get("query")),
        }
        body = _body(spec)
        if body:
            request["body"] = body
        item: Dict[str, Any] = {"name": ep.name or ep.path or "接口", "request": request}
        groups.setdefault(folders.get(ep.folder_id), []).append(item)

    items: List[Dict[str, Any]] = []
    for folder, reqs in groups.items():
        if folder:
            items.append({"name": folder, "item": reqs})
        else:
            items.extend(reqs)

    return {
        "info": {"name": proj.name if proj else "导出", "schema": _POSTMAN_SCHEMA},
        "item": items,
    }


def export_postman(db: Session, project_id: int, opts: Optional[ExportOptions] = None) -> tuple[str, str, str]:
    doc = build_postman(db, project_id, opts)
    content = json.dumps(doc, ensure_ascii=False, indent=2)
    return content, "application/json", f"postman-project-{project_id}.json"

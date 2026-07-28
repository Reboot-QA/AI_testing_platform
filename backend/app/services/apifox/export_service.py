"""Apifox → OpenAPI / Swagger 导出（导入的逆过程）。

支持：范围过滤（全部 / 按标签 / 指定接口 / 排除标签）、规格版本（OpenAPI 3.0/3.1、Swagger 2.0）、
文件格式（JSON/YAML）。纯读、纯函数式组装。
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml
from sqlalchemy.orm import Session

from app.models.project import Project
from app.repositories.apifox import endpoint_repo, schema_repo

_BODY_MEDIA = {"json": "application/json", "xml": "application/xml", "raw": "text/plain"}
_BODY_WITH_PAYLOAD = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass
class ExportOptions:
    spec_version: str = "3.0"  # 3.0 | 3.1 | swagger2
    file_format: str = "json"  # json | yaml
    scope: str = "all"  # all | tags | endpoints
    tags: List[str] = field(default_factory=list)
    exclude_tags: List[str] = field(default_factory=list)
    endpoint_ids: List[int] = field(default_factory=list)


def _spec(ep) -> dict:
    try:
        return json.loads(ep.request_spec) if ep.request_spec else {}
    except (ValueError, TypeError):
        return {}


def _rows(spec_rows: Optional[List[dict]]) -> List[dict]:
    """取启用、有 key 的行。"""
    out = []
    for r in spec_rows or []:
        key = str(r.get("key") or "").strip()
        if key and r.get("enabled") is not False:
            out.append(r)
    return out


# ---------- 过滤 ----------
def _collect(db: Session, project_id: int, opts: ExportOptions):
    proj = db.query(Project).filter(Project.id == project_id).first()
    folders = {f.id: f.name for f in endpoint_repo.list_folders(db, project_id)}
    schemas = schema_repo.list_schemas(db, project_id)
    endpoints = []
    ids = set(opts.endpoint_ids or [])
    inc = set(opts.tags or [])
    exc = set(opts.exclude_tags or [])
    for ep in endpoint_repo.list_endpoints(db, project_id):  # 已排除软删除
        tag = folders.get(ep.folder_id)
        if opts.scope == "endpoints" and ep.id not in ids:
            continue
        if opts.scope == "tags" and inc and tag not in inc:
            continue
        if exc and tag in exc:
            continue
        endpoints.append(ep)
    return proj, endpoints, folders, schemas


# ---------- OpenAPI 3.x ----------
def _oas_params(rows: Optional[List[dict]], location: str) -> List[dict]:
    out: List[dict] = []
    for r in _rows(rows):
        p: Dict[str, Any] = {
            "name": str(r.get("key")).strip(),
            "in": location,
            "required": location == "path",
            "schema": {"type": r.get("type") or "string"},
        }
        if r.get("desc"):
            p["description"] = r["desc"]
        if r.get("value"):
            p["example"] = r["value"]
        out.append(p)
    return out


def _oas_body(body: Optional[dict]) -> Optional[dict]:
    btype = str((body or {}).get("type") or "none")
    if btype in ("json", "raw", "xml"):
        raw = str((body or {}).get("raw") or "")
        media = _BODY_MEDIA[btype]
        content: Dict[str, Any] = {media: {}}
        if raw:
            if btype == "json":
                try:
                    content[media]["example"] = json.loads(raw)
                except (ValueError, TypeError):
                    content[media]["example"] = raw
            else:
                content[media]["example"] = raw
        return {"content": content}
    if btype in ("form-data", "urlencoded"):
        props: Dict[str, Any] = {r["key"].strip(): {"type": r.get("type") or "string"} for r in _rows((body or {}).get("form"))}
        media = "multipart/form-data" if btype == "form-data" else "application/x-www-form-urlencoded"
        return {"content": {media: {"schema": {"type": "object", "properties": props}}}}
    return None


def build_openapi(db: Session, project_id: int, opts: Optional[ExportOptions] = None) -> Dict[str, Any]:
    opts = opts or ExportOptions()
    proj, endpoints, folders, schemas = _collect(db, project_id, opts)
    paths: Dict[str, Any] = {}
    for ep in endpoints:
        spec = _spec(ep)
        op: Dict[str, Any] = {"summary": ep.name, "operationId": f"ep{ep.id}"}
        if ep.description:
            op["description"] = ep.description
        if ep.folder_id and ep.folder_id in folders:
            op["tags"] = [folders[ep.folder_id]]
        params = (
            _oas_params(spec.get("query"), "query")
            + _oas_params(spec.get("path_params"), "path")
            + _oas_params(spec.get("headers"), "header")
        )
        if params:
            op["parameters"] = params
        if ep.method.upper() in _BODY_WITH_PAYLOAD:
            rb = _oas_body(spec.get("body"))
            if rb:
                op["requestBody"] = rb
        resp: Dict[str, Any] = {"200": {"description": "OK"}}
        if ep.response_schema_id:
            sch = schema_repo.get_schema(db, ep.response_schema_id)
            if sch:
                resp["200"]["content"] = {
                    "application/json": {"schema": {"$ref": f"#/components/schemas/{sch.name}"}}
                }
        op["responses"] = resp
        paths.setdefault(ep.path or "/", {})[ep.method.lower()] = op

    components_schemas: Dict[str, Any] = {}
    for sch in schemas:
        try:
            components_schemas[sch.name] = json.loads(sch.json_schema) if sch.json_schema else {}
        except (ValueError, TypeError):
            components_schemas[sch.name] = {}

    version = "3.1.0" if opts.spec_version == "3.1" else "3.0.0"
    doc: Dict[str, Any] = {
        "openapi": version,
        "info": {"title": proj.name if proj else "导出", "version": "1.0.0"},
        "paths": paths,
    }
    if components_schemas:
        doc["components"] = {"schemas": components_schemas}
    return doc


# ---------- Swagger 2.0 ----------
def _sw2_params(rows: Optional[List[dict]], location: str) -> List[dict]:
    out = []
    for r in _rows(rows):
        p: Dict[str, Any] = {
            "name": str(r.get("key")).strip(),
            "in": location,
            "required": location == "path",
            "type": r.get("type") or "string",
        }
        if r.get("desc"):
            p["description"] = r["desc"]
        out.append(p)
    return out


def build_swagger2(db: Session, project_id: int, opts: Optional[ExportOptions] = None) -> Dict[str, Any]:
    opts = opts or ExportOptions()
    proj, endpoints, folders, schemas = _collect(db, project_id, opts)
    paths: Dict[str, Any] = {}
    for ep in endpoints:
        spec = _spec(ep)
        op: Dict[str, Any] = {"summary": ep.name, "operationId": f"ep{ep.id}"}
        if ep.description:
            op["description"] = ep.description
        if ep.folder_id and ep.folder_id in folders:
            op["tags"] = [folders[ep.folder_id]]
        params = (
            _sw2_params(spec.get("query"), "query")
            + _sw2_params(spec.get("path_params"), "path")
            + _sw2_params(spec.get("headers"), "header")
        )
        # Swagger 2.0 的 body 是单个 in:body 参数
        if ep.method.upper() in _BODY_WITH_PAYLOAD:
            body = spec.get("body") or {}
            if str(body.get("type") or "none") in ("json", "raw", "xml"):
                schema: Dict[str, Any] = {"type": "object"}
                if ep.response_schema_id:  # 无请求模型时给通用对象
                    pass
                params.append({"name": "body", "in": "body", "required": False, "schema": schema})
        if params:
            op["parameters"] = params
        resp: Dict[str, Any] = {"200": {"description": "OK"}}
        if ep.response_schema_id:
            sch = schema_repo.get_schema(db, ep.response_schema_id)
            if sch:
                resp["200"]["schema"] = {"$ref": f"#/definitions/{sch.name}"}
        op["responses"] = resp
        paths.setdefault(ep.path or "/", {})[ep.method.lower()] = op

    definitions: Dict[str, Any] = {}
    for sch in schemas:
        try:
            definitions[sch.name] = json.loads(sch.json_schema) if sch.json_schema else {}
        except (ValueError, TypeError):
            definitions[sch.name] = {}

    doc: Dict[str, Any] = {
        "swagger": "2.0",
        "info": {"title": proj.name if proj else "导出", "version": "1.0.0"},
        "paths": paths,
    }
    if definitions:
        doc["definitions"] = definitions
    return doc


# ---------- 出口：序列化 + 文件名 ----------
def export(db: Session, project_id: int, opts: Optional[ExportOptions] = None) -> tuple[str, str, str]:
    """返回 (内容文本, media_type, 文件名)。"""
    opts = opts or ExportOptions()
    doc = build_swagger2(db, project_id, opts) if opts.spec_version == "swagger2" else build_openapi(db, project_id, opts)
    base = f"openapi-project-{project_id}"
    if opts.file_format == "yaml":
        content = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
        return content, "application/yaml", f"{base}.yaml"
    content = json.dumps(doc, ensure_ascii=False, indent=2)
    return content, "application/json", f"{base}.json"

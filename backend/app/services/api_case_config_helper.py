import json
from typing import Any, Dict, List, Optional

from app.models.api_automation import ApiTestCase
from app.services.api_request_builder import META_KEY, extract_meta_from_headers
from app.services.api_data_ai_service import _infer_body_type, _normalize_body_type


def _infer_body_type_local(body: Optional[str]) -> str:
    return _infer_body_type(body)


def _resolve_body_type(meta: Dict[str, Any], body: Optional[str]) -> str:
    meta_type = meta.get("body_type") or "none"
    return _normalize_body_type(str(meta_type), body)


def _active_kv_rows(rows: Any) -> List[Dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    result: List[Dict[str, Any]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        if not key or item.get("enabled") is False:
            continue
        result.append(item)
    return result


def _load_headers(case: ApiTestCase) -> Dict[str, Any]:
    if not case.headers:
        return {}
    try:
        parsed = json.loads(case.headers)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def parse_case_generation_context(case: ApiTestCase) -> Dict[str, Any]:
    meta = extract_meta_from_headers(case.headers)
    body_type = _resolve_body_type(meta, case.body)
    body_stores = meta.get("body_stores") if isinstance(meta.get("body_stores"), dict) else {}

    body = case.body or ""
    if body_type == "json":
        body = str(body_stores.get("json") or case.body or "")
    elif body_type == "raw":
        body = str(body_stores.get("raw") or case.body or "")
    elif body_type == "form-data":
        rows = body_stores.get("form_data") or meta.get("form_body") or []
        if not rows and case.body:
            try:
                parsed = json.loads(case.body)
                rows = parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                rows = []
        body = json.dumps(rows, ensure_ascii=False) if rows else (case.body or "")
    elif body_type == "urlencoded":
        rows = body_stores.get("urlencoded") or meta.get("form_body") or []
        if not rows and case.body:
            try:
                parsed = json.loads(case.body)
                rows = parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                rows = []
        body = json.dumps(rows, ensure_ascii=False) if rows else (case.body or "")

    return {
        "name": case.name,
        "method": case.method,
        "path": case.path or "/",
        "body": body,
        "body_type": body_type,
        "headers": case.headers,
        "query_params": _active_kv_rows(meta.get("query")),
        "path_params": _active_kv_rows(meta.get("path_vars")),
    }


def apply_generated_data_to_case(case: ApiTestCase, generated: Dict[str, Any]) -> bool:
    raw_headers = _load_headers(case)
    meta = raw_headers.get(META_KEY, {}) if isinstance(raw_headers.get(META_KEY), dict) else {}
    body_type = _resolve_body_type(meta, case.body)
    body_stores = meta.get("body_stores") if isinstance(meta.get("body_stores"), dict) else {}
    changed = False

    new_body = generated.get("body")
    if new_body:
        resolved_type = _normalize_body_type(body_type, case.body or new_body)
        if resolved_type in {"none", "json"} or _infer_body_type_local(str(new_body)) == "json":
            resolved_type = "json"
            body_stores["json"] = new_body
            case.body = new_body
            meta["body_type"] = "json"
            changed = True
        elif resolved_type == "raw":
            body_stores["raw"] = new_body
            case.body = new_body
            meta["body_type"] = "raw"
            changed = True
        elif resolved_type in {"form-data", "urlencoded"}:
            case.body = new_body
            meta["body_type"] = resolved_type
            try:
                rows = json.loads(new_body)
                if isinstance(rows, list):
                    store_key = "form_data" if resolved_type == "form-data" else "urlencoded"
                    body_stores[store_key] = rows
                    meta["form_body"] = rows
            except json.JSONDecodeError:
                pass
            changed = True

    query_map = generated.get("query") if isinstance(generated.get("query"), dict) else {}
    query_rows = meta.get("query")
    if not isinstance(query_rows, list):
        query_rows = []
    for row in query_rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        if key and key in query_map:
            row["value"] = query_map[key]
            changed = True

    path_map = generated.get("path") if isinstance(generated.get("path"), dict) else {}
    path_rows = meta.get("path_vars")
    if not isinstance(path_rows, list):
        path_rows = []
    for row in path_rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or "").strip()
        if key and key in path_map:
            row["value"] = path_map[key]
            changed = True

    if changed:
        meta["body_stores"] = body_stores
        meta["query"] = query_rows
        meta["path_vars"] = path_rows
        raw_headers[META_KEY] = meta
        case.headers = json.dumps(raw_headers, ensure_ascii=False, indent=2)
    return changed

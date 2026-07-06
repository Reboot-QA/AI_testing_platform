import json
import base64
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urljoin, urlparse, urlunparse, parse_qsl

META_KEY = "__meta"
VARIABLE_PATTERN = re.compile(r"\{\{([^}]+)\}\}")


def _variables_from_meta(meta: Dict[str, Any]) -> Dict[str, str]:
    variables: Dict[str, str] = {}
    for item in meta.get("variables") or []:
        if not item.get("enabled", True):
            continue
        key = (item.get("key") or "").strip()
        if key:
            variables[key] = str(item.get("value") or "")
    return variables


def extract_meta_from_headers(case_headers_text: Optional[str]) -> Dict[str, Any]:
    if not case_headers_text:
        return {}
    try:
        raw_headers = json.loads(case_headers_text)
    except json.JSONDecodeError:
        return {}
    meta = raw_headers.get(META_KEY, {}) or {}
    return meta if isinstance(meta, dict) else {}


def iter_data_drive_variable_sets(meta: Dict[str, Any]) -> List[Tuple[str, Dict[str, str]]]:
    """Return (label, variables) for each enabled data-drive row, or a single default set."""
    base = _variables_from_meta(meta)
    data_drive = meta.get("data_drive") or {}
    if not data_drive.get("enabled"):
        return [("默认变量", dict(base))]

    rows = [row for row in (data_drive.get("rows") or []) if row.get("enabled", True)]
    if not rows:
        return [("默认变量", dict(base))]

    result: List[Tuple[str, Dict[str, str]]] = []
    for index, row in enumerate(rows):
        values = row.get("values") or {}
        merged = dict(base)
        if isinstance(values, dict):
            for key, value in values.items():
                name = str(key or "").strip()
                if name:
                    merged[name] = "" if value is None else str(value)
        label = str(row.get("name") or "").strip() or f"数据集{index + 1}"
        result.append((label, merged))
    return result


def _apply_variables(text: Optional[str], variables: Dict[str, str]) -> str:
    if text is None:
        return ""
    if not variables:
        return str(text)

    def repl(match) -> str:
        name = match.group(1).strip()
        return variables.get(name, match.group(0))

    return VARIABLE_PATTERN.sub(repl, str(text))


def _substitute_kv_rows(rows: List[Dict[str, Any]], variables: Dict[str, str]) -> List[Dict[str, Any]]:
    if not rows or not variables:
        return rows
    result: List[Dict[str, Any]] = []
    for item in rows:
        row = dict(item)
        if row.get("key"):
            row["key"] = _apply_variables(str(row.get("key") or ""), variables).strip() or row.get("key")
        row["value"] = _apply_variables(str(row.get("value") or ""), variables)
        result.append(row)
    return result

def _apply_path_vars(path: str, path_vars: List[Dict[str, Any]]) -> str:
    result = path or "/"
    for item in path_vars:
        if not item.get("enabled", True):
            continue
        key = (item.get("key") or "").strip()
        if not key:
            continue
        result = result.replace("{" + key + "}", str(item.get("value") or ""))
    return result


def _apply_query(path: str, query_rows: List[Dict[str, Any]]) -> str:
    if "?" in path:
        pathname, existing = path.split("?", 1)
    else:
        pathname, existing = path, ""
    params = dict(parse_qsl(existing, keep_blank_values=True))
    for item in query_rows:
        if not item.get("enabled", True):
            continue
        key = (item.get("key") or "").strip()
        if not key:
            continue
        params[key] = str(item.get("value") or "")
    if not params:
        return pathname
    return f"{pathname}?{urlencode(params)}"


def _stringify_form_field_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _form_rows_from_body_text(case_body: Optional[str]) -> List[Dict[str, Any]]:
    if not case_body or not case_body.strip():
        return []
    try:
        parsed = json.loads(case_body)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [
            {"key": key, "value": _stringify_form_field_value(value), "enabled": True}
            for key, value in parsed.items()
            if key != META_KEY
        ]
    return []


def _build_body_and_content_type(body_type: str, body_text: str, form_body: List[Dict[str, Any]]) -> Tuple[str, Optional[str], Optional[Dict[str, Any]]]:
    body_type = (body_type or "raw").lower()
    if body_type == "none":
        return "", None, None
    if body_type == "json":
        return body_text or "", "application/json", None
    if body_type == "raw":
        return body_text or "", None, None
    rows = [item for item in form_body if item.get("enabled", True) and (item.get("key") or "").strip()]
    if body_type == "urlencoded":
        data = {item["key"].strip(): str(item.get("value") or "") for item in rows}
        return urlencode(data), "application/x-www-form-urlencoded", None
    if body_type == "form-data":
        data = {item["key"].strip(): str(item.get("value") or "") for item in rows}
        return "", "multipart/form-data", data
    return body_text or "", None, None


def prepare_case_request(
    case_headers_text: Optional[str],
    case_path: str,
    case_method: str,
    case_body: Optional[str],
    environment: Optional[Any],
    variables: Optional[Dict[str, str]] = None,
) -> Tuple[str, str, Dict[str, str], str, Dict[str, str]]:
    default_headers = {}
    if environment and environment.default_headers:
        try:
            default_headers = json.loads(environment.default_headers)
        except json.JSONDecodeError:
            default_headers = {}

    raw_headers = {}
    if case_headers_text:
        try:
            raw_headers = json.loads(case_headers_text)
        except json.JSONDecodeError:
            raw_headers = {}

    meta = raw_headers.pop(META_KEY, {}) or {}
    if not isinstance(meta, dict):
        meta = {}

    if variables is None:
        variables = _variables_from_meta(meta)
    default_headers = {key: _apply_variables(value, variables) for key, value in default_headers.items()}

    headers = {**(default_headers or {}), **raw_headers}
    headers = {key: _apply_variables(value, variables) for key, value in headers.items()}

    auth = meta.get("auth") or {}
    auth = {
        **auth,
        "token": _apply_variables(str(auth.get("token") or ""), variables),
        "username": _apply_variables(str(auth.get("username") or ""), variables),
        "password": _apply_variables(str(auth.get("password") or ""), variables),
    }
    auth_type = (auth.get("type") or "none").lower()
    if auth_type == "bearer" and auth.get("token"):
        token = str(auth["token"]).strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        headers["Authorization"] = f"Bearer {token}"
    elif auth_type == "basic" and auth.get("username"):
        token = base64.b64encode(f"{auth['username']}:{auth.get('password', '')}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    elif meta.get("authorization_header"):
        headers["Authorization"] = _apply_variables(str(meta["authorization_header"]), variables)

    cookies = _substitute_kv_rows(meta.get("cookies") or [], variables)
    cookie_pairs = []
    for item in cookies:
        if not item.get("enabled", True):
            continue
        key = (item.get("key") or "").strip()
        if key:
            cookie_pairs.append(f"{key}={item.get('value', '')}")
    if cookie_pairs:
        headers["Cookie"] = "; ".join(cookie_pairs)

    case_path = _apply_variables(case_path or "/", variables)
    path = _apply_path_vars(case_path, _substitute_kv_rows(meta.get("path_vars") or [], variables))
    path = _apply_query(path, _substitute_kv_rows(meta.get("query") or [], variables))

    base_url = environment.base_url if environment else ""
    if (path or "").startswith("http://") or (path or "").startswith("https://"):
        url = path
    else:
        url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))

    body_type = meta.get("body_type") or "raw"
    form_body = meta.get("form_body") or []
    if not form_body:
        form_body = _form_rows_from_body_text(case_body)
    form_body = _substitute_kv_rows(form_body, variables)
    case_body = _apply_variables(case_body or "", variables)

    body, content_type, form_data = _build_body_and_content_type(body_type, case_body or "", form_body)
    if content_type and "Content-Type" not in headers and "content-type" not in {k.lower() for k in headers}:
        headers["Content-Type"] = content_type

    method = (case_method or "GET").upper()
    request_data = {"form_data": form_data} if form_data else {}
    return method, url, headers, body, request_data

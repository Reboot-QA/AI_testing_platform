"""Apifox 执行引擎 · HTTP 请求构建（URL / 参数 / 头 / 认证 / body 拼装）。

按接口 spec + 环境 + 变量拼装出可直接交给 httpx 的请求计划（含 body 快照）。
纯函数、不发请求、不落库；依赖底层 variables（插值 / 行转字典）。
"""

import base64
import json
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.apifox.variable import ApifoxEnvironment
from app.services.apifox.variables import _rows_to_dict, apply_vars


def _select_base_url(environment: Optional[ApifoxEnvironment], server_name: Optional[str]) -> str:
    """按接口选定的命名前置 URL 取 base_url；未选/未命中 → 环境默认前置 URL(base_url)。"""
    if environment is None:
        return ""
    if server_name:
        for server in environment.servers or []:
            if server.name == server_name:
                return (server.base_url or "").rstrip("/")
    return (environment.base_url or "").rstrip("/")


def build_request(
    endpoint: ApifoxEndpoint,
    spec: Dict[str, Any],
    environment: Optional[ApifoxEnvironment],
    variables: Dict[str, str],
    global_params: List,
    binary_loader: Optional[Callable[[int], Optional[Tuple[bytes, str]]]] = None,
) -> Dict[str, Any]:
    path = apply_vars(endpoint.path, variables)
    for row in spec.get("path_params") or []:
        key = str(row.get("key") or "").strip()
        if key and row.get("enabled") is not False:
            path = path.replace("{%s}" % key, apply_vars(str(row.get("value") or ""), variables))

    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        base = _select_base_url(environment, getattr(endpoint, "server_name", None))
        if not base:
            raise ValueError("未选择环境或环境未配置前置 URL，且接口路径不是绝对地址")
        url = base + ("/" + path.lstrip("/") if path else "")

    params = _rows_to_dict(spec.get("query") or [], variables)
    headers = _rows_to_dict(spec.get("headers") or [], variables)
    cookies = _rows_to_dict(spec.get("cookies") or [], variables)

    # 全局参数附加（header/query/cookie；body 位置暂不支持）
    for gp in global_params:
        if not gp.enabled:
            continue
        value = apply_vars(gp.value or "", variables)
        if gp.location == "header":
            headers.setdefault(gp.key, value)
        elif gp.location == "query":
            params.setdefault(gp.key, value)
        elif gp.location == "cookie":
            cookies.setdefault(gp.key, value)

    auth = spec.get("auth") or {}
    auth_type = auth.get("type") or "none"
    if auth_type == "bearer" and auth.get("token"):
        headers["Authorization"] = "Bearer " + apply_vars(auth["token"], variables)
    elif auth_type == "basic":
        raw = f"{apply_vars(auth.get('username') or '', variables)}:{apply_vars(auth.get('password') or '', variables)}"
        headers["Authorization"] = "Basic " + base64.b64encode(raw.encode("utf-8")).decode("ascii")

    if cookies:
        headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())

    body = spec.get("body") or {}
    body_type = body.get("type") or "none"
    request_kwargs: Dict[str, Any] = {}
    body_snapshot = ""
    if body_type in ("json", "raw", "xml"):
        content = apply_vars(body.get("raw") or "", variables)
        if content:
            request_kwargs["content"] = content
            body_snapshot = content
        if body_type == "json":
            headers.setdefault("Content-Type", "application/json")
        elif body_type == "xml":
            headers.setdefault("Content-Type", "application/xml")
    elif body_type == "graphql":
        query = apply_vars(body.get("graphql_query") or "", variables)
        raw_vars = apply_vars(body.get("graphql_variables") or "", variables).strip()
        try:  # variables 为 JSON 文本；非法则按空对象发送，不因脏输入抛异常
            parsed_vars = json.loads(raw_vars) if raw_vars else {}
        except (ValueError, TypeError):
            parsed_vars = {}
        # graphql 选定即发（query 可为空），与其余类型的 if content 判空刻意不同
        content = json.dumps({"query": query, "variables": parsed_vars}, ensure_ascii=False)
        request_kwargs["content"] = content
        body_snapshot = content
        headers.setdefault("Content-Type", "application/json")
    elif body_type == "binary":
        file_id = body.get("file_id")
        loaded = binary_loader(int(file_id)) if (file_id and binary_loader) else None
        if loaded:
            data, ctype = loaded
            request_kwargs["content"] = data
            if ctype:
                headers.setdefault("Content-Type", ctype)
            body_snapshot = f"<binary {len(data)} bytes>"
    elif body_type == "form-data":
        form = _rows_to_dict(body.get("form") or [], variables)
        if form:
            request_kwargs["files"] = {k: (None, v) for k, v in form.items()}
            body_snapshot = json.dumps(form, ensure_ascii=False)
    elif body_type == "urlencoded":
        form = _rows_to_dict(body.get("form") or [], variables)
        if form:
            request_kwargs["data"] = form
            body_snapshot = json.dumps(form, ensure_ascii=False)

    return {
        "method": endpoint.method,
        "url": url,
        "params": params,
        "headers": headers,
        "request_kwargs": request_kwargs,
        "body_snapshot": body_snapshot,
    }

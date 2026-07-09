"""Apifox 执行引擎 · 纯执行层（变量解析 / 请求构建 / 单用例执行）。

复用旧模块纯函数：断言判定 _evaluate_assertion、提取取值 _extract_value_by_source、
脚本执行 run_pre_script/run_post_script。生成器编排与 run 落库在 run_service。
提取的 environment/global 作用域写当前用户本地值（不污染团队远程值）。
"""

import base64
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.apifox.variable import ApifoxEnvironment, ApifoxEnvironmentVariable, ApifoxGlobalVariable
from app.repositories.apifox import global_param_repo, script_repo, variable_repo
from app.services.api_response_extract import _extract_value_by_source
from app.services.api_runner_service import _evaluate_assertion
from app.services.api_script_runner import run_post_script, run_pre_script

VARIABLE_PATTERN = re.compile(r"\{\{([^}]+)\}\}")
HTTP_TIMEOUT = 30.0
MAX_BODY_SNAPSHOT = 20000


def apply_vars(text: Optional[str], variables: Dict[str, str]) -> str:
    if not text:
        return ""
    return VARIABLE_PATTERN.sub(
        lambda m: variables.get(m.group(1).strip(), m.group(0)), str(text)
    )


def _loads(text: Optional[str], fallback):
    if not text:
        return fallback
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return fallback


def _rows_to_dict(rows: List[Dict[str, Any]], variables: Dict[str, str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for row in rows or []:
        key = str(row.get("key") or "").strip()
        if not key or row.get("enabled") is False:
            continue
        result[key] = apply_vars(str(row.get("value") or ""), variables)
    return result


# ---------- 变量解析（local ?? remote，enabled） ----------
def resolve_env_vars(db: Session, environment_id: Optional[int], user_id: int) -> Dict[str, str]:
    if not environment_id:
        return {}
    result: Dict[str, str] = {}
    for var in variable_repo.list_env_vars(db, environment_id):
        if not var.enabled:
            continue
        local = variable_repo.get_env_local(db, var.id, user_id)
        value = local.local_value if local else var.remote_value
        result[var.key] = value or ""
    return result


def resolve_global_vars(db: Session, project_id: int, user_id: int) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for var in variable_repo.list_global_vars(db, project_id):
        if not var.enabled:
            continue
        local = variable_repo.get_global_local(db, var.id, user_id)
        value = local.local_value if local else var.remote_value
        result[var.key] = value or ""
    return result


def merge_vars(*layers: Dict[str, str]) -> Dict[str, str]:
    """后者覆盖前者：global < env < runtime < case/data_drive。"""
    merged: Dict[str, str] = {}
    for layer in layers:
        merged.update(layer or {})
    return merged


def case_variable_rows(case: ApifoxEndpointCase) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for row in _loads(case.variables, []):
        key = str(row.get("key") or "").strip()
        if key and row.get("enabled") is not False:
            result[key] = str(row.get("value") or "")
    return result


def data_drive_rows(case: ApifoxEndpointCase) -> List[Optional[Dict[str, str]]]:
    """返回执行迭代列表：未启用数据驱动 → [None]；启用 → 各 enabled 行的 values。"""
    drive = _loads(case.data_drive, {})
    result: List[Optional[Dict[str, str]]] = []
    if drive.get("enabled"):
        for row in drive.get("rows") or []:
            if row.get("enabled") is not False:
                result.append(
                    {str(k): str(v or "") for k, v in (row.get("values") or {}).items()}
                )
    if not result:
        result.append(None)
    return result


# ---------- 请求构建 ----------
def build_request(
    endpoint: ApifoxEndpoint,
    spec: Dict[str, Any],
    environment: Optional[ApifoxEnvironment],
    variables: Dict[str, str],
    global_params: List,
) -> Dict[str, Any]:
    path = apply_vars(endpoint.path, variables)
    for row in spec.get("path_params") or []:
        key = str(row.get("key") or "").strip()
        if key and row.get("enabled") is not False:
            path = path.replace("{%s}" % key, apply_vars(str(row.get("value") or ""), variables))

    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        base = (environment.base_url or "").rstrip("/") if environment else ""
        if not base:
            raise ValueError("未选择环境或环境未配置 base_url，且接口路径不是绝对地址")
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
    if body_type in ("json", "raw"):
        content = apply_vars(body.get("raw") or "", variables)
        if content:
            request_kwargs["content"] = content
            body_snapshot = content
        if body_type == "json":
            headers.setdefault("Content-Type", "application/json")
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


# ---------- 断言/提取/脚本 ----------
def _adapt_assertion(row) -> Dict[str, Any]:
    data: Dict[str, Any] = {"type": row.type, "expected": row.expected}
    if row.type == "response_time":
        data["max_ms"] = row.expected
    elif row.type == "header":
        data["name"] = row.path or ""
    elif row.type == "json_path":
        data["path"] = row.path or ""
    return data


def evaluate_assertions(rows, response: httpx.Response, duration_ms: float) -> Tuple[bool, List[Dict]]:
    results: List[Dict[str, Any]] = []
    all_passed = True
    for row in rows:
        if not row.enabled:
            continue
        result = _evaluate_assertion(_adapt_assertion(row), response, duration_ms)
        # 行表 expected 为字符串，json_path 实际值可能是数字/布尔——补字符串宽松比较
        if not result.get("passed") and row.type == "json_path":
            if str(result.get("actual")) == str(row.expected):
                result["passed"] = True
                result["message"] += "（字符串等价）"
        results.append(result)
        if not result.get("passed"):
            all_passed = False
    if not results:
        ok = 200 <= response.status_code < 400
        results.append({
            "type": "status_code", "passed": ok,
            "expected": "2xx/3xx", "actual": response.status_code,
            "message": f"默认校验：状态码 {response.status_code}",
        })
        all_passed = ok
    return all_passed, results


def run_extracts(
    rows, response: httpx.Response, request_snapshot: Dict[str, Any], duration_ms: float
) -> Tuple[Dict[str, str], List[Dict[str, str]], List[Dict[str, Any]]]:
    """返回 (runtime更新, scoped[{key,value,scope}], 结果卡片)。"""
    extracted: Dict[str, str] = {}
    scoped: List[Dict[str, str]] = []
    results: List[Dict[str, Any]] = []
    for row in rows:
        if not row.enabled or not row.var_name:
            continue
        ok, value, err = _extract_value_by_source(
            row.source, row.path or "", response, request_snapshot, duration_ms
        )
        results.append({
            "var_name": row.var_name, "source": row.source, "scope": row.scope,
            "passed": ok, "value": value if ok else "", "message": err or "",
        })
        if ok:
            extracted[row.var_name] = value
            if row.scope in ("environment", "global"):
                scoped.append({"key": row.var_name, "value": value, "scope": row.scope})
    return extracted, scoped, results


def run_case_scripts(
    db: Session, case_id: int, phase: str, variables: Dict[str, str],
    response: Optional[httpx.Response] = None, duration_ms: float = 0,
) -> Tuple[Dict[str, str], List[str], Optional[str]]:
    """按顺序执行该 phase 引用的库脚本，串联 variables。返回 (variables, logs, first_error)。"""
    logs: List[str] = []
    first_error: Optional[str] = None
    current = dict(variables)
    for link in script_repo.list_case_scripts(db, case_id):
        if link.phase != phase or not link.enabled:
            continue
        script = script_repo.get_script(db, link.script_id)
        if not script or not (script.content or "").strip():
            continue
        if phase == "pre":
            current, script_logs, error = run_pre_script(script.content, script.lang, current)
        else:
            current, script_logs, error = run_post_script(
                script.content, script.lang, current,
                response_body=response.text if response is not None else None,
                response_status=response.status_code if response is not None else None,
                response_headers=dict(response.headers) if response is not None else None,
            )
        logs.extend([f"[{script.name}] {line}" for line in script_logs])
        if error and first_error is None:
            first_error = f"[{script.name}] {error}"
    return current, logs, first_error


def persist_scoped_extracts(
    db: Session, project_id: int, environment_id: Optional[int], user_id: int,
    scoped: List[Dict[str, str]],
) -> None:
    """environment/global 作用域提取 → 写当前用户本地值；变量不存在则先建远程行(remote=None)。"""
    for item in scoped:
        key, value, scope = item["key"], item["value"], item["scope"]
        if scope == "environment":
            if not environment_id:
                continue
            env_var = next(
                (v for v in variable_repo.list_env_vars(db, environment_id) if v.key == key),
                None,
            )
            if env_var is None:
                env_var = ApifoxEnvironmentVariable(environment_id=environment_id, key=key)
                variable_repo.add(db, env_var)
            variable_repo.upsert_env_local(db, env_var.id, user_id, value)
        elif scope == "global":
            global_var = next(
                (v for v in variable_repo.list_global_vars(db, project_id) if v.key == key),
                None,
            )
            if global_var is None:
                global_var = ApifoxGlobalVariable(project_id=project_id, key=key)
                variable_repo.add(db, global_var)
            variable_repo.upsert_global_local(db, global_var.id, user_id, value)
    db.commit()


def _truncate(text: str, limit: int = MAX_BODY_SNAPSHOT) -> str:
    return text if len(text) <= limit else text[:limit] + "...(截断)"


# ---------- 单用例执行 ----------
def execute_case(
    db: Session,
    case: ApifoxEndpointCase,
    endpoint: ApifoxEndpoint,
    environment: Optional[ApifoxEnvironment],
    variables: Dict[str, str],
    assertions,
    extracts,
) -> Tuple[str, Dict[str, Any]]:
    """执行一次用例（一组变量），返回 (passed|failed, detail 快照)。不落库。"""
    detail: Dict[str, Any] = {
        "method": endpoint.method, "url": "", "request_headers": {}, "request_body": "",
        "response_status": None, "response_headers": {}, "response_body": "",
        "duration_ms": 0.0, "assertion_results": [], "extract_results": [],
        "script_logs": [], "extracted": {}, "scoped": [], "error_message": None,
    }

    # 前置脚本（error → failed）
    variables, pre_logs, pre_error = run_case_scripts(db, case.id, "pre", variables)
    detail["script_logs"].extend(pre_logs)
    if pre_error:
        detail["error_message"] = f"前置脚本失败: {pre_error}"
        return "failed", detail

    spec = _loads(case.request_spec, {})
    try:
        plan = build_request(
            endpoint, spec, environment, variables,
            global_param_repo.list_params(db, case.project_id),
        )
    except ValueError as exc:
        detail["error_message"] = str(exc)
        return "failed", detail

    detail["url"] = plan["url"]
    detail["request_headers"] = plan["headers"]
    detail["request_body"] = plan["body_snapshot"]

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            response = client.request(
                plan["method"], plan["url"],
                params=plan["params"] or None,
                headers=plan["headers"] or None,
                **plan["request_kwargs"],
            )
    except httpx.RequestError as exc:
        detail["duration_ms"] = (time.perf_counter() - started) * 1000
        detail["error_message"] = f"请求失败: {exc}"
        return "failed", detail
    duration_ms = (time.perf_counter() - started) * 1000

    detail["duration_ms"] = duration_ms
    detail["response_status"] = response.status_code
    detail["response_headers"] = dict(response.headers)
    detail["response_body"] = _truncate(response.text)

    passed, assertion_results = evaluate_assertions(assertions, response, duration_ms)
    detail["assertion_results"] = assertion_results

    request_snapshot = {"headers": plan["headers"], "body": plan["body_snapshot"]}
    extracted, scoped, extract_results = run_extracts(
        extracts, response, request_snapshot, duration_ms
    )
    detail["extracted"] = extracted
    detail["scoped"] = scoped
    detail["extract_results"] = extract_results

    # 后置脚本（error 仅记录）
    variables.update(extracted)
    _, post_logs, post_error = run_case_scripts(
        db, case.id, "post", variables, response=response, duration_ms=duration_ms
    )
    detail["script_logs"].extend(post_logs)
    if post_error:
        detail["script_logs"].append(f"后置脚本错误: {post_error}")

    return ("passed" if passed else "failed"), detail

"""Apifox 执行引擎 · facade + 单用例执行编排。

纯函数按职责拆到同目录子模块：变量插值 variables / 操作符比较 operators /
请求构建 request_builder / 流程控制 flow_control。本模块保留断言评估、结果提取、
脚本执行、作用域落库与单用例编排 execute_case，并 re-export 上述子模块的对外符号，
保持既有导入路径（debug_service / run_service / scenario_service / 测试依赖之）不变。

复用旧模块纯函数：断言判定 _evaluate_assertion、提取取值 _extract_value_by_source、
脚本执行 run_pre_script/run_post_script。生成器编排与 run 落库在 run_service。
提取的 environment/global 作用域写当前用户本地值（不污染团队远程值）。
"""

import json
import time
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.apifox.variable import ApifoxEnvironment, ApifoxEnvironmentVariable, ApifoxGlobalVariable
from app.repositories.apifox import (
    endpoint_repo,
    global_param_repo,
    schema_repo,
    script_repo,
    variable_repo,
)
from app.services.api_response_extract import _extract_value_by_source
from app.services.api_runner_service import _evaluate_assertion, _extract_json_path
from app.services.api_script_runner import run_post_script, run_pre_script
from app.services.apifox import contract_service, schema_ref, upload_service
from app.services.apifox.flow_control import MAX_LOOP_ITERATIONS, evaluate_condition, loop_iterations
from app.services.apifox.operators import CONDITION_OPERATORS, _apply_operator
from app.services.apifox.request_builder import build_request
from app.services.apifox.variables import (
    _loads,
    apply_vars,
    case_variable_rows,
    data_drive_rows,
    merge_vars,
    resolve_env_vars,
    resolve_global_vars,
)

# 子模块对外符号经本 facade re-export，保持调用方既有导入路径不变
__all__ = [
    "apply_vars", "resolve_env_vars", "resolve_global_vars", "merge_vars",
    "case_variable_rows", "data_drive_rows",
    "CONDITION_OPERATORS", "MAX_LOOP_ITERATIONS", "evaluate_condition", "loop_iterations",
    "build_request",
    "evaluate_assertions", "run_extracts", "run_script_links",
    "persist_scoped_extracts", "execute_case",
    "HTTP_TIMEOUT", "MAX_BODY_SNAPSHOT", "make_http_client",
]

HTTP_TIMEOUT = 30.0
MAX_BODY_SNAPSHOT = 20000


def make_http_client(plan: Dict[str, Any]) -> httpx.Client:
    """按请求计划的 settings 构建 httpx 客户端：未设超时回落 HTTP_TIMEOUT；SSL/重定向所配即所用。"""
    timeout = plan.get("timeout")
    return httpx.Client(
        timeout=timeout if timeout is not None else HTTP_TIMEOUT,
        follow_redirects=plan.get("follow_redirects", True),
        verify=plan.get("verify_ssl", True),
    )

_OP_WITH_OPERATOR = {"status_code", "json_path", "header"}


# ---------- 断言 ----------
def _adapt_assertion(row) -> Dict[str, Any]:
    data: Dict[str, Any] = {"type": row.type, "expected": row.expected}
    if row.type == "response_time":
        data["max_ms"] = row.expected
    elif row.type == "header":
        data["name"] = row.path or ""
    elif row.type == "json_path":
        data["path"] = row.path or ""
    return data


def _evaluate_with_operator(row, response: httpx.Response) -> Dict[str, Any]:
    if row.type == "status_code":
        actual: Any = response.status_code
    elif row.type == "header":
        actual = response.headers.get(row.path or "", "")
    else:  # json_path
        try:
            payload = response.json()
        except (json.JSONDecodeError, ValueError):
            payload = None
        actual = _extract_json_path(payload, row.path or "")
    passed, message = _apply_operator(actual, row.expected, getattr(row, "operator", "eq"))
    return {
        "type": row.type, "operator": getattr(row, "operator", "eq") or "eq",
        "passed": passed, "expected": row.expected, "actual": actual, "message": message,
    }


def evaluate_assertions(rows, response: httpx.Response, duration_ms: float) -> Tuple[bool, List[Dict]]:
    results: List[Dict[str, Any]] = []
    all_passed = True
    for row in rows:
        if not row.enabled:
            continue
        # status_code/json_path/header 走操作符比较；contains/response_time 保持既有语义（含隐式操作符）
        if row.type in _OP_WITH_OPERATOR:
            result = _evaluate_with_operator(row, response)
        else:
            result = _evaluate_assertion(_adapt_assertion(row), response, duration_ms)
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


# ---------- 提取 ----------
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


# ---------- 脚本 ----------
def run_script_links(
    db: Session, links, is_pre: bool, variables: Dict[str, str],
    response: Optional[httpx.Response] = None, duration_ms: float = 0,
) -> Tuple[Dict[str, str], List[str], Optional[str]]:
    """按给定顺序执行一组已过滤 phase 的脚本引用，串联 variables。返回 (variables, logs, first_error)。

    接口级与用例级脚本合并叠加：调用方按序拼接 links（前置 接口在前、后置 用例在前）。
    """
    logs: List[str] = []
    first_error: Optional[str] = None
    current = dict(variables)
    for link in links:
        if not link.enabled:
            continue
        script = script_repo.get_script(db, link.script_id)
        if not script or not (script.content or "").strip():
            continue
        if is_pre:
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


def _phase_links(links, phase: str):
    return [link for link in links if link.phase == phase]


# ---------- 作用域提取落库 ----------
def persist_scoped_extracts(
    db: Session, project_id: int, environment_id: Optional[int], user_id: Optional[int],
    scoped: List[Dict[str, str]],
) -> None:
    """environment/global 作用域提取的落库。

    手动运行(user_id 有值)→ 写该用户本地值，不污染团队远程值；
    定时运行(user_id=None)→ 写远程值（团队共享，如刷新 token 全员受益）。
    变量不存在则先建远程行。
    """
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
            if user_id is None:
                env_var.remote_value = value
            else:
                variable_repo.upsert_env_local(db, env_var.id, user_id, value)
        elif scope == "global":
            global_var = next(
                (v for v in variable_repo.list_global_vars(db, project_id) if v.key == key),
                None,
            )
            if global_var is None:
                global_var = ApifoxGlobalVariable(project_id=project_id, key=key)
                variable_repo.add(db, global_var)
            if user_id is None:
                global_var.remote_value = value
            else:
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
        "script_logs": [], "extracted": {}, "scoped": [], "contract_result": None,
        "error_message": None,
    }

    # 处理器合并叠加：接口级 + 用例级
    ep_scripts = script_repo.list_endpoint_scripts(db, endpoint.id)
    case_scripts = script_repo.list_case_scripts(db, case.id)
    ep_assertions = endpoint_repo.list_endpoint_assertions(db, endpoint.id)
    ep_extracts = endpoint_repo.list_endpoint_extracts(db, endpoint.id)

    # 前置脚本（接口-pre 先于 用例-pre；error → failed）
    pre_links = _phase_links(ep_scripts, "pre") + _phase_links(case_scripts, "pre")
    variables, pre_logs, pre_error = run_script_links(db, pre_links, True, variables)
    detail["script_logs"].extend(pre_logs)
    if pre_error:
        detail["error_message"] = f"前置脚本失败: {pre_error}"
        return "failed", detail

    spec = _loads(case.request_spec, {})
    try:
        plan = build_request(
            endpoint, spec, environment, variables,
            global_param_repo.list_params(db, case.project_id),
            binary_loader=upload_service.make_binary_loader(db, case.project_id),
        )
    except ValueError as exc:
        detail["error_message"] = str(exc)
        return "failed", detail

    detail["url"] = plan["url"]
    detail["request_headers"] = plan["headers"]
    detail["request_body"] = plan["body_snapshot"]

    started = time.perf_counter()
    try:
        with make_http_client(plan) as client:
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

    # 断言并集：接口断言 + 用例断言都评估
    passed, assertion_results = evaluate_assertions(
        list(ep_assertions) + list(assertions), response, duration_ms
    )
    detail["assertion_results"] = assertion_results

    # 契约校验：接口绑了响应模型才校验；contract_strict 时契约败拉低 step 状态
    if endpoint.response_schema_id:
        schema = schema_repo.get_schema(db, endpoint.response_schema_id)
        if schema and schema.project_id == case.project_id:
            resolved = schema_ref.resolve_schema_text(db, case.project_id, schema.json_schema)
            contract = contract_service.validate_response(resolved, response)
            contract["schema_name"] = schema.name
            detail["contract_result"] = contract
            if endpoint.contract_strict and not contract["passed"]:
                passed = False

    # 提取并集：接口提取在前，用例同名变量后写覆盖
    request_snapshot = {"headers": plan["headers"], "body": plan["body_snapshot"]}
    extracted, scoped, extract_results = run_extracts(
        list(ep_extracts) + list(extracts), response, request_snapshot, duration_ms
    )
    detail["extracted"] = extracted
    detail["scoped"] = scoped
    detail["extract_results"] = extract_results

    # 后置脚本（用例-post 先于 接口-post；error 仅记录）
    variables.update(extracted)
    post_links = _phase_links(case_scripts, "post") + _phase_links(ep_scripts, "post")
    _, post_logs, post_error = run_script_links(
        db, post_links, False, variables, response=response, duration_ms=duration_ms
    )
    detail["script_logs"].extend(post_logs)
    if post_error:
        detail["script_logs"].append(f"后置脚本错误: {post_error}")

    return ("passed" if passed else "failed"), detail


def execute_http_request(
    db: Session, project_id: int, method: str, path: str, server_name: Optional[str],
    request_spec: Dict[str, Any], assertions, extracts,
    environment: Optional[ApifoxEnvironment], variables: Dict[str, str],
) -> Tuple[str, Dict[str, Any]]:
    """执行一个内联 HTTP 请求（场景裸步骤）：假 endpoint(鸭子类型) 复用 build_request + 断言 + 提取。

    不含接口级处理器/脚本/契约（裸步骤自带 method/path/request_spec/assertions/extracts）。不落库。
    """
    detail: Dict[str, Any] = {
        "method": method, "url": "", "request_headers": {}, "request_body": "",
        "response_status": None, "response_headers": {}, "response_body": "",
        "duration_ms": 0.0, "assertion_results": [], "extract_results": [],
        "script_logs": [], "extracted": {}, "scoped": [], "contract_result": None,
        "error_message": None,
    }
    # 鸭子类型：build_request 只读 .path/.method/.server_name，裸步骤无真实 endpoint 行
    fake_endpoint = SimpleNamespace(path=path, method=method, server_name=server_name)
    try:
        plan = build_request(
            fake_endpoint, request_spec, environment, variables,  # type: ignore[arg-type]
            global_param_repo.list_params(db, project_id),
            binary_loader=upload_service.make_binary_loader(db, project_id),
        )
    except ValueError as exc:
        detail["error_message"] = str(exc)
        return "failed", detail

    detail["url"] = plan["url"]
    detail["request_headers"] = plan["headers"]
    detail["request_body"] = plan["body_snapshot"]

    started = time.perf_counter()
    try:
        with make_http_client(plan) as client:
            response = client.request(
                plan["method"], plan["url"],
                params=plan["params"] or None, headers=plan["headers"] or None,
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
    extracted, scoped, extract_results = run_extracts(extracts, response, request_snapshot, duration_ms)
    detail["extracted"] = extracted
    detail["scoped"] = scoped
    detail["extract_results"] = extract_results

    return ("passed" if passed else "failed"), detail

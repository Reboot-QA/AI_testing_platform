"""Apifox 执行引擎 · facade + 单用例执行编排。

纯函数按职责拆到同目录子模块：变量插值 variables / 操作符比较 operators /
请求构建 request_builder / 流程控制 flow_control。本模块保留断言评估、结果提取、
脚本执行、作用域落库与单用例编排 execute_case，并 re-export 上述子模块的对外符号，
保持既有导入路径（debug_service / run_service / scenario_service / 测试依赖之）不变。

复用同目录 apifox 纯函数（D1 已从老模块搬入）：断言判定 assertions._evaluate_assertion、
提取取值 response_extract._extract_value_by_source、脚本执行 script_runner.run_pre/post_script。
生成器编排与 run 落库在 run_service。
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
from app.services.apifox import contract_service, schema_ref, upload_service
from app.services.apifox.assertions import _evaluate_assertion, _extract_json_path
from app.services.apifox.flow_control import MAX_LOOP_ITERATIONS, evaluate_condition, loop_iterations
from app.services.apifox.operators import CONDITION_OPERATORS, _apply_operator
from app.services.apifox.request_builder import build_request
from app.services.apifox.response_extract import _extract_value_by_source
from app.services.apifox.script_runner import run_post_script, run_pre_script
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


# ---------- 登录态跨步骤透传（场景级 cookie jar + token 自动捕获/注入） ----------
# 响应体里常见的 token 字段名（大小写不敏感），含 data./result./body. 一层嵌套。
_TOKEN_KEYS = {"token", "access_token", "accesstoken", "jwt", "id_token", "auth_token"}
_TOKEN_NEST_KEYS = ("data", "result", "body")


def _bearer_from_headers(headers: Dict[str, str]) -> Optional[str]:
    """取手动写死的 Bearer token（去前缀）用于向后传递；非 Bearer 方案不转发（避免注成 Bearer Token xxx）。"""
    for key, value in headers.items():
        if key.lower() == "authorization":
            val = (value or "").strip()
            return val[7:].strip() or None if val.lower().startswith("bearer ") else None
    return None


def _has_authorization(headers: Dict[str, str]) -> bool:
    """该步是否已显式设置 Authorization（任何方案）——手动优先，不自动注入。"""
    return any(key.lower() == "authorization" for key in headers)


def _find_token(obj: Dict[str, Any]) -> Optional[str]:
    for key, value in obj.items():
        if key.lower() in _TOKEN_KEYS and isinstance(value, str) and value.strip():
            return value.strip()
    for nest in _TOKEN_NEST_KEYS:
        sub = obj.get(nest)
        if isinstance(sub, dict):
            found = _find_token(sub)
            if found:
                return found
    return None


def _capture_token_from_body(response: httpx.Response) -> Optional[str]:
    try:
        data = response.json()
    except ValueError:
        return None
    return _find_token(data) if isinstance(data, dict) else None


def _send_request(
    plan: Dict[str, Any],
    detail: Dict[str, Any],
    cookie_jar: Optional[httpx.Cookies] = None,
    auth_token: Optional[str] = None,
) -> Optional[httpx.Response]:
    """统一发送：Authorization 自动注入（手动优先）+ cookie jar 透传 + token 捕获。

    记录 req/resp 快照与 detail["captured_token"]（供上层更新传递中的 token）。
    网络错误时置 detail 并返回 None。cookie_jar/auth_token 为 None 即现状行为。
    """
    headers = plan["headers"]
    if auth_token and not _has_authorization(headers):  # 该步未显式设 Authorization → 自动注入
        headers["Authorization"] = f"Bearer {auth_token}"

    detail["url"] = plan["url"]
    detail["request_headers"] = headers
    detail["request_body"] = plan["body_snapshot"]
    detail["warnings"] = plan.get("warnings", [])

    started = time.perf_counter()
    try:
        with make_http_client(plan) as client:
            response = client.request(
                plan["method"], plan["url"],
                params=plan["params"] or None,
                headers=headers or None,
                cookies=cookie_jar,
                **plan["request_kwargs"],
            )
    except httpx.RequestError as exc:
        detail["duration_ms"] = (time.perf_counter() - started) * 1000
        detail["error_message"] = f"请求失败: {exc}"
        return None
    detail["duration_ms"] = (time.perf_counter() - started) * 1000

    if cookie_jar is not None:
        cookie_jar.update(response.cookies)
    # 传递中的 token：手动写死的 Bearer 优先更新；响应体新 token 再覆盖（refresh 场景）
    captured = _capture_token_from_body(response) or _bearer_from_headers(headers)
    detail["captured_token"] = captured

    detail["response_status"] = response.status_code
    detail["response_headers"] = dict(response.headers)
    detail["response_body"] = _truncate(response.text)
    return response


# ---------- 单用例执行 ----------
_MAX_PROC_WAIT_MS = 60000


class _Op:
    """有序处理器项（鸭子兼容 evaluate_assertions/run_extracts/run_script_links 的属性访问）。

    不引 routers.schemas 的 ProcessorRow，避免 run_engine 触发 routers 包的循环导入。
    """

    __slots__ = (
        "kind", "enabled", "script_id", "wait_ms", "type", "path", "operator",
        "expected", "var_name", "source", "scope", "response_schema_id", "contract_strict",
    )

    def __init__(self, **kw):
        self.kind = kw.get("kind")
        self.enabled = kw.get("enabled", True)
        self.script_id = kw.get("script_id")
        self.wait_ms = kw.get("wait_ms")
        self.type = kw.get("type")
        self.path = kw.get("path")
        self.operator = kw.get("operator") or "eq"
        self.expected = kw.get("expected")
        self.var_name = kw.get("var_name")
        self.source = kw.get("source") or "response_json"
        self.scope = kw.get("scope") or "temporary"
        self.response_schema_id = kw.get("response_schema_id")
        self.contract_strict = kw.get("contract_strict")


def _parse_processors(raw) -> List["_Op"]:
    data = _loads(raw, None)
    if not isinstance(data, list):
        return []
    return [_Op(**x) for x in data if isinstance(x, dict)]


def _script_op(link) -> "_Op":
    return _Op(kind="script", script_id=link.script_id, enabled=link.enabled)


def _fallback_pre_ops(pre_script_links) -> List["_Op"]:
    """无前置处理器时，把旧前置脚本按序转成 script 处理器（保持旧行为）。"""
    return [_script_op(link) for link in pre_script_links]


def _fallback_post_ops(assertions, contract_schema_id, contract_strict, extracts, post_script_links):
    """无后置处理器时，把旧的 断言→契约→提取→后置脚本 按旧固定顺序转成处理器列表。"""
    ops: List[_Op] = [
        _Op(kind="assertion", type=a.type, path=a.path, operator=a.operator,
            expected=a.expected, enabled=a.enabled)
        for a in assertions
    ]
    if contract_schema_id:
        ops.append(_Op(kind="contract", response_schema_id=contract_schema_id,
                       contract_strict=bool(contract_strict), enabled=True))
    ops += [
        _Op(kind="extract", var_name=e.var_name, source=e.source, path=e.path,
            scope=e.scope, enabled=e.enabled)
        for e in extracts
    ]
    ops += [_script_op(link) for link in post_script_links]
    return ops


def _run_pre_ops(db: Session, ops, variables: Dict[str, str], detail: Dict[str, Any]):
    """按序执行前置 ops（script/wait）。返回 (variables, error)；脚本 error 短路。"""
    for op in ops:
        if not op.enabled:
            continue
        if op.kind == "script" and op.script_id:
            variables, logs, error = run_script_links(db, [op], True, variables)
            detail["script_logs"].extend(logs)
            if error:
                return variables, error
        elif op.kind == "wait":
            time.sleep(min(op.wait_ms or 0, _MAX_PROC_WAIT_MS) / 1000)
    return variables, None


def _run_post_ops(db, ops, response, detail, variables, request_snapshot, duration_ms, project_id):
    """按序执行后置 ops（script/wait/assertion/extract/contract）。返回 passed。"""
    passed = True
    saw_assertion = False
    for op in ops:
        if not op.enabled:
            continue
        if op.kind == "assertion":
            saw_assertion = True
            ok, results = evaluate_assertions([op], response, duration_ms)
            detail["assertion_results"].extend(results)
            passed = passed and ok
        elif op.kind == "extract":
            extracted, scoped, results = run_extracts([op], response, request_snapshot, duration_ms)
            detail["extracted"].update(extracted)
            detail["scoped"].extend(scoped)
            detail["extract_results"].extend(results)
            variables.update(extracted)  # 立即注入，供后续 script op 使用
        elif op.kind == "contract" and op.response_schema_id:
            schema = schema_repo.get_schema(db, op.response_schema_id)
            if schema and schema.project_id == project_id:
                resolved = schema_ref.resolve_schema_text(db, project_id, schema.json_schema)
                contract = contract_service.validate_response(resolved, response)
                contract["schema_name"] = schema.name
                detail["contract_result"] = contract
                if op.contract_strict and not contract["passed"]:
                    passed = False
        elif op.kind == "script" and op.script_id:
            variables, logs, error = run_script_links(
                db, [op], False, variables, response=response, duration_ms=duration_ms
            )
            detail["script_logs"].extend(logs)
            if error:
                detail["script_logs"].append(f"后置脚本错误: {error}")
        elif op.kind == "wait":
            time.sleep(min(op.wait_ms or 0, _MAX_PROC_WAIT_MS) / 1000)
    if not saw_assertion:  # 无断言 op → 沿用默认 2xx/3xx 校验
        ok, results = evaluate_assertions([], response, duration_ms)
        detail["assertion_results"].extend(results)
        passed = passed and ok
    return passed


def execute_case(
    db: Session,
    case: ApifoxEndpointCase,
    endpoint: ApifoxEndpoint,
    environment: Optional[ApifoxEnvironment],
    variables: Dict[str, str],
    assertions,
    extracts,
    cookie_jar: Optional[httpx.Cookies] = None,
    auth_token: Optional[str] = None,
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

    # 有序处理器（自由混排）：任一层为空回退该层旧字段；四处皆空则完全走旧固定管线（零回归）
    case_pre_procs = _parse_processors(case.pre_processors)
    case_post_procs = _parse_processors(case.post_processors)
    ep_pre_procs = _parse_processors(endpoint.pre_processors)
    ep_post_procs = _parse_processors(endpoint.post_processors)
    use_processors = bool(case_pre_procs or case_post_procs or ep_pre_procs or ep_post_procs)

    # 前置（接口在前、用例在后）
    if use_processors:
        pre_ops = (ep_pre_procs or _fallback_pre_ops(_phase_links(ep_scripts, "pre"))) + (
            case_pre_procs or _fallback_pre_ops(_phase_links(case_scripts, "pre"))
        )
        variables, pre_error = _run_pre_ops(db, pre_ops, variables, detail)
    else:
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

    response = _send_request(plan, detail, cookie_jar=cookie_jar, auth_token=auth_token)
    if response is None:
        return "failed", detail
    duration_ms = detail["duration_ms"]

    request_snapshot = {"headers": plan["headers"], "body": plan["body_snapshot"]}

    if use_processors:
        # 后置按序自由混排（用例层在前、接口层在后；层内空则回退旧字段的固定子序）
        post_ops = (
            case_post_procs
            or _fallback_post_ops(assertions, None, False, extracts, _phase_links(case_scripts, "post"))
        ) + (
            ep_post_procs
            or _fallback_post_ops(
                ep_assertions, endpoint.response_schema_id, endpoint.contract_strict,
                ep_extracts, _phase_links(ep_scripts, "post"),
            )
        )
        passed = _run_post_ops(
            db, post_ops, response, detail, variables, request_snapshot, duration_ms, case.project_id
        )
        return ("passed" if passed else "failed"), detail

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
    cookie_jar: Optional[httpx.Cookies] = None,
    auth_token: Optional[str] = None,
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

    response = _send_request(plan, detail, cookie_jar=cookie_jar, auth_token=auth_token)
    if response is None:
        return "failed", detail
    duration_ms = detail["duration_ms"]

    passed, assertion_results = evaluate_assertions(assertions, response, duration_ms)
    detail["assertion_results"] = assertion_results

    request_snapshot = {"headers": plan["headers"], "body": plan["body_snapshot"]}
    extracted, scoped, extract_results = run_extracts(extracts, response, request_snapshot, duration_ms)
    detail["extracted"] = extracted
    detail["scoped"] = scoped
    detail["extract_results"] = extract_results

    return ("passed" if passed else "failed"), detail

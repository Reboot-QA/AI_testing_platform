"""Apifox 接口调试：用 request_spec + 环境直接发一次请求，并执行传入的接口级处理器。

复用 run_engine 的纯函数（build_request/变量解析/发送/脚本/断言/提取/数据库）；**不建用例、不落 run**。
environment/global 作用域的提取会写入当前用户本地值（与场景运行一致），供后续调试 {{变量}} 引用；
temporary 作用域仅当次内存有效。支持编辑态未保存的 request_spec 与处理器直接发。
"""

import time
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.models.apifox.endpoint import ApifoxEndpoint
from app.repositories.apifox import global_param_repo, schema_repo, variable_repo
from app.services.apifox import contract_service, schema_ref, upload_service
from app.services.apifox import run_engine as engine


def _sleep_waits(waits: List[int]) -> None:
    """执行有序处理器中的 wait（等待）项；单项上限与执行引擎一致，避免调试阻塞过久。"""
    for ms in waits:
        time.sleep(min(int(ms or 0), engine._MAX_PROC_WAIT_MS) / 1000)


def _base_result(plan: Dict[str, Any], script_logs: List[str]) -> Dict[str, Any]:
    return {
        "method": plan["method"],
        "url": plan["url"],
        "request_headers": plan["headers"],
        "request_body": plan["body_snapshot"],
        "warnings": plan.get("warnings", []),
        "status_code": None,
        "response_headers": {},
        "response_body": "",
        "duration_ms": 0.0,
        "error": None,
        "assertion_results": [],
        "extract_results": [],
        "script_logs": list(script_logs),
        "console_db_logs": [],
        "contract_result": None,
    }


def debug_send(
    db: Session,
    project_id: int,
    method: str,
    path: str,
    request_spec: Dict[str, Any],
    environment_id: Optional[int],
    user_id: Optional[int],
    server_name: Optional[str] = None,
    assertions: Optional[List[Any]] = None,
    extracts: Optional[List[Any]] = None,
    pre_scripts: Optional[List[Any]] = None,
    post_scripts: Optional[List[Any]] = None,
    pre_inline: Optional[List[Any]] = None,
    post_inline: Optional[List[Any]] = None,
    response_schema_id: Optional[int] = None,
    pre_waits: Optional[List[int]] = None,
    post_waits: Optional[List[int]] = None,
    pre_processors: Optional[List[Any]] = None,
    post_processors: Optional[List[Any]] = None,
    console_print_db: bool = False,
) -> Dict[str, Any]:
    assertions = assertions or []
    extracts = extracts or []
    pre_scripts = pre_scripts or []
    post_scripts = post_scripts or []
    pre_inline = pre_inline or []
    post_inline = post_inline or []
    pre_waits = pre_waits or []
    post_waits = post_waits or []
    pre_processors = pre_processors or []
    post_processors = post_processors or []

    environment = variable_repo.get_environment(db, environment_id) if environment_id else None
    env_vars = engine.resolve_env_vars(db, environment_id, user_id)
    global_vars = engine.resolve_global_vars(db, project_id, user_id)
    variables = engine.merge_vars(global_vars, env_vars)

    use_ordered = bool(pre_processors or post_processors)
    detail: Dict[str, Any] = {
        "script_logs": [],
        "console_db_logs": [],
        "console_print_db": console_print_db if use_ordered else False,
        "extract_results": [],
        "extracted": {},
        "scoped": [],
        "assertion_results": [],
        "contract_result": None,
    }

    if use_ordered:
        variables, pre_error = engine._run_pre_ops(db, pre_processors, variables, detail, environment)
        if pre_error:
            endpoint = ApifoxEndpoint(
                method=(method or "GET").upper(), path=path or "", server_name=server_name
            )
            try:
                plan = engine.build_request(
                    endpoint,
                    request_spec or {},
                    environment,
                    variables,
                    global_param_repo.list_params(db, project_id),
                    binary_loader=upload_service.make_binary_loader(db, project_id),
                )
            except ValueError as exc:
                return {
                    "method": (method or "GET").upper(),
                    "url": "",
                    "request_headers": {},
                    "request_body": "",
                    "warnings": [],
                    "status_code": None,
                    "response_headers": {},
                    "response_body": "",
                    "duration_ms": 0.0,
                    "error": str(exc),
                    "assertion_results": [],
                    "extract_results": detail.get("extract_results", []),
                    "script_logs": detail["script_logs"],
                    "console_db_logs": detail.get("console_db_logs", []),
                    "contract_result": None,
                }
            result = _base_result(plan, detail["script_logs"])
            result["console_db_logs"] = detail.get("console_db_logs", [])
            result["error"] = pre_error
            result["extract_results"] = detail.get("extract_results", [])
            return result
    else:
        variables, pre_logs, pre_error = engine.run_script_links(db, pre_scripts, True, variables)
        detail["script_logs"].extend(pre_logs)
        if pre_error:
            detail["script_logs"].append(f"前置脚本错误: {pre_error}")
        for row in pre_inline:
            if not getattr(row, "enabled", True) or not (getattr(row, "content", "") or "").strip():
                continue
            variables, inline_logs, inline_error = engine.run_pre_script(row.content, row.lang, variables)
            detail["script_logs"].extend([f"[内联脚本] {line}" for line in inline_logs])
            if inline_error:
                detail["script_logs"].append(f"前置内联脚本错误: {inline_error}")
        _sleep_waits(pre_waits)

    endpoint = ApifoxEndpoint(
        method=(method or "GET").upper(), path=path or "", server_name=server_name
    )
    plan = engine.build_request(
        endpoint,
        request_spec or {},
        environment,
        variables,
        global_param_repo.list_params(db, project_id),
        binary_loader=upload_service.make_binary_loader(db, project_id),
    )

    result = _base_result(plan, detail["script_logs"])
    result["console_db_logs"] = detail.get("console_db_logs", [])

    started = time.perf_counter()
    try:
        with engine.make_http_client(plan) as client:
            response = client.request(
                plan["method"],
                plan["url"],
                params=plan["params"] or None,
                headers=plan["headers"] or None,
                **plan["request_kwargs"],
            )
    except httpx.RequestError as exc:
        result["duration_ms"] = (time.perf_counter() - started) * 1000
        result["error"] = f"请求失败: {exc}"
        result["console_db_logs"] = detail.get("console_db_logs", [])
        return result

    duration_ms = (time.perf_counter() - started) * 1000
    result["duration_ms"] = duration_ms
    result["status_code"] = response.status_code
    result["response_headers"] = dict(response.headers)
    result["response_body"] = engine._truncate(response.text)

    request_snapshot = {"headers": plan["headers"], "body": plan["body_snapshot"]}

    if use_ordered:
        engine._run_post_ops(
            db,
            post_processors,
            response,
            detail,
            variables,
            request_snapshot,
            duration_ms,
            project_id,
            environment,
        )
        result["script_logs"] = detail["script_logs"]
        result["console_db_logs"] = detail.get("console_db_logs", [])
        result["assertion_results"] = detail.get("assertion_results", [])
        result["extract_results"] = detail.get("extract_results", [])
        if detail.get("contract_result"):
            result["contract_result"] = detail["contract_result"]
        if detail.get("scoped"):
            engine.persist_scoped_extracts(db, project_id, environment_id, user_id, detail["scoped"])
        return result

    # —— 旧式分列处理器（无 database 步骤）——
    if extracts:
        extracted, scoped, extract_results = engine.run_extracts(
            extracts, response, request_snapshot, duration_ms
        )
        result["extract_results"] = extract_results
        variables.update(extracted)
        if scoped:
            engine.persist_scoped_extracts(db, project_id, environment_id, user_id, scoped)

    if assertions:
        _passed, assertion_results = engine.evaluate_assertions(assertions, response, duration_ms)
        result["assertion_results"] = assertion_results

    if response_schema_id:
        schema = schema_repo.get_schema(db, response_schema_id)
        if schema and schema.project_id == project_id:
            resolved = schema_ref.resolve_schema_text(db, project_id, schema.json_schema)
            contract = contract_service.validate_response(resolved, response)
            contract["schema_name"] = schema.name
            result["contract_result"] = contract

    variables, post_logs, post_error = engine.run_script_links(
        db, post_scripts, False, variables, response=response, duration_ms=duration_ms
    )
    result["script_logs"].extend(post_logs)
    if post_error:
        result["script_logs"].append(f"后置脚本错误: {post_error}")
    for row in post_inline:
        if not getattr(row, "enabled", True) or not (getattr(row, "content", "") or "").strip():
            continue
        variables, inline_logs, inline_error = engine.run_post_script(
            row.content,
            row.lang,
            variables,
            response_body=response.text,
            response_status=response.status_code,
            response_headers=dict(response.headers),
        )
        result["script_logs"].extend([f"[内联脚本] {line}" for line in inline_logs])
        if inline_error:
            result["script_logs"].append(f"后置内联脚本错误: {inline_error}")

    _sleep_waits(post_waits)
    return result

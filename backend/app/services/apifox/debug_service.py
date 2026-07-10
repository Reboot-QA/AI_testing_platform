"""Apifox 接口调试：用 request_spec + 环境直接发一次请求，并执行传入的接口级处理器。

复用 run_engine 的纯函数（build_request/变量解析/发送/脚本/断言/提取）；**不建用例、
不落 run、提取的 environment/global 作用域不落库**（纯调试，只展示结果）。
支持编辑态未保存的 request_spec 与处理器直接发。
"""

import time
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from app.models.apifox.endpoint import ApifoxEndpoint
from app.repositories.apifox import global_param_repo, schema_repo, variable_repo
from app.services.apifox import contract_service
from app.services.apifox import run_engine as engine


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
    response_schema_id: Optional[int] = None,
) -> Dict[str, Any]:
    assertions = assertions or []
    extracts = extracts or []
    pre_scripts = pre_scripts or []
    post_scripts = post_scripts or []

    environment = variable_repo.get_environment(db, environment_id) if environment_id else None
    env_vars = engine.resolve_env_vars(db, environment_id, user_id)
    global_vars = engine.resolve_global_vars(db, project_id, user_id)
    variables = engine.merge_vars(global_vars, env_vars)

    script_logs: List[str] = []
    # 前置脚本先跑（可能设置请求引用的变量）
    variables, pre_logs, pre_error = engine.run_script_links(db, pre_scripts, True, variables)
    script_logs.extend(pre_logs)
    if pre_error:
        script_logs.append(f"前置脚本错误: {pre_error}")

    endpoint = ApifoxEndpoint(
        method=(method or "GET").upper(), path=path or "", server_name=server_name
    )
    plan = engine.build_request(
        endpoint, request_spec or {}, environment, variables,
        global_param_repo.list_params(db, project_id),
    )  # 无环境且相对路径时 raise ValueError（router 转 400）

    result: Dict[str, Any] = {
        "method": plan["method"],
        "url": plan["url"],
        "request_headers": plan["headers"],
        "request_body": plan["body_snapshot"],
        "status_code": None,
        "response_headers": {},
        "response_body": "",
        "duration_ms": 0.0,
        "error": None,
        "assertion_results": [],
        "extract_results": [],
        "script_logs": script_logs,
        "contract_result": None,
    }

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=engine.HTTP_TIMEOUT, follow_redirects=True) as client:
            response = client.request(
                plan["method"], plan["url"],
                params=plan["params"] or None,
                headers=plan["headers"] or None,
                **plan["request_kwargs"],
            )
    except httpx.RequestError as exc:
        result["duration_ms"] = (time.perf_counter() - started) * 1000
        result["error"] = f"请求失败: {exc}"
        return result

    duration_ms = (time.perf_counter() - started) * 1000
    result["duration_ms"] = duration_ms
    result["status_code"] = response.status_code
    result["response_headers"] = dict(response.headers)
    result["response_body"] = engine._truncate(response.text)

    # 提取（scope 提取不落库，仅展示）
    if extracts:
        request_snapshot = {"headers": plan["headers"], "body": plan["body_snapshot"]}
        extracted, _scoped, extract_results = engine.run_extracts(
            extracts, response, request_snapshot, duration_ms
        )
        result["extract_results"] = extract_results
        variables.update(extracted)

    # 断言（为空则不校验、不返回结果）
    if assertions:
        _passed, assertion_results = engine.evaluate_assertions(assertions, response, duration_ms)
        result["assertion_results"] = assertion_results

    # 契约校验（绑了响应模型才校验，调试只展示不判失败）
    if response_schema_id:
        schema = schema_repo.get_schema(db, response_schema_id)
        if schema and schema.project_id == project_id:
            contract = contract_service.validate_response(schema.json_schema or "", response)
            contract["schema_name"] = schema.name
            result["contract_result"] = contract

    # 后置脚本
    _, post_logs, post_error = engine.run_script_links(
        db, post_scripts, False, variables, response=response, duration_ms=duration_ms
    )
    script_logs.extend(post_logs)
    if post_error:
        script_logs.append(f"后置脚本错误: {post_error}")

    return result

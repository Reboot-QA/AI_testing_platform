"""Apifox 接口调试：用 request_spec + 环境直接发一次请求。

复用 run_engine 的纯函数（build_request/变量解析/发送）；**不建用例、不落 run、
不跑断言/提取/脚本**。支持编辑态未保存的 request_spec 直接发。
"""

import time
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from app.models.apifox.endpoint import ApifoxEndpoint
from app.repositories.apifox import global_param_repo, variable_repo
from app.services.apifox import run_engine as engine


def debug_send(
    db: Session,
    project_id: int,
    method: str,
    path: str,
    request_spec: Dict[str, Any],
    environment_id: Optional[int],
    user_id: Optional[int],
) -> Dict[str, Any]:
    environment = variable_repo.get_environment(db, environment_id) if environment_id else None
    env_vars = engine.resolve_env_vars(db, environment_id, user_id)
    global_vars = engine.resolve_global_vars(db, project_id, user_id)
    variables = engine.merge_vars(global_vars, env_vars)

    endpoint = ApifoxEndpoint(method=(method or "GET").upper(), path=path or "")
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

    result["duration_ms"] = (time.perf_counter() - started) * 1000
    result["status_code"] = response.status_code
    result["response_headers"] = dict(response.headers)
    result["response_body"] = engine._truncate(response.text)
    return result

"""Apifox 执行引擎 · 编排层（SSE 生成器：建 run → 逐步执行落库 yield → 收尾统计）。

事件契约沿旧模块：start / step / done / error（error 由路由层兜底转换）。
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

import httpx
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.run import ApifoxRun, ApifoxRunStep
from app.models.apifox.scenario import ApifoxScenario, ApifoxScenarioStep
from app.models.apifox.suite import ApifoxSuite, ApifoxSuiteItem
from app.models.apifox.variable import ApifoxEnvironment
from app.repositories.apifox import (
    case_repo,
    database_conn_repo,
    dataset_repo,
    endpoint_repo,
    run_repo,
    scenario_repo,
    suite_repo,
)
from app.routers.apifox.case_schemas import AssertionRow, ExtractRow
from app.services.apifox import db_executor
from app.services.apifox import run_engine as engine

logger = logging.getLogger(__name__)

MAX_WAIT_MS = 60000
_MAX_DEPTH = 50


class _BreakLoop(Exception):
    """break 步骤信号：向上穿透嵌套生成器，由最近的循环 _run_loop_block 捕获后终止该循环。"""


class _ContinueLoop(Exception):
    """continue 步骤信号：跳过循环体剩余步骤，进入最近循环的下一轮。"""


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _count_case_steps(db: Session, case: ApifoxEndpointCase) -> int:
    return len(engine.data_drive_rows(case, db))


def _count_scenario_steps(db: Session, scenario_id: int, depth: int = 0) -> int:
    if depth > _MAX_DEPTH:
        return 0
    by_parent = scenario_repo.group_steps_by_parent(db, scenario_id)
    return _count_steps(db, by_parent, by_parent.get(None, []), depth)


def _count_steps(
    db: Session,
    by_parent: Dict[Optional[int], List[ApifoxScenarioStep]],
    steps: List[ApifoxScenarioStep],
    depth: int,
) -> int:
    total = 0
    for step in steps:
        if not step.enabled:
            continue
        if step.type == "case" and step.ref_case_id:
            case = case_repo.get_case(db, step.ref_case_id)
            if case:
                total += _count_case_steps(db, case)
        elif step.type == "wait":
            total += 1
        elif step.type in ("break", "continue"):
            total += 1
        elif step.type == "db":
            total += 1
        elif step.type == "http":
            total += 1
        elif step.type == "scenario" and step.ref_scenario_id:
            total += _count_scenario_steps(db, step.ref_scenario_id, depth + 1)
        elif step.type == "group" and depth < _MAX_DEPTH:
            total += _count_steps(db, by_parent, by_parent.get(step.id, []), depth + 1)
        elif step.type == "if" and depth < _MAX_DEPTH:
            # total 仅进度估算：运行前未知走哪支，取两分支较大值，保证实际 index 不超 total
            children = by_parent.get(step.id, [])
            then_steps = [c for c in children if c.type != "else"]
            counts = [_count_steps(db, by_parent, then_steps, depth + 1)]
            else_step = next((c for c in children if c.type == "else"), None)
            if else_step:
                counts.append(_count_steps(db, by_parent, by_parent.get(else_step.id, []), depth + 1))
            total += max(counts)
        elif step.type == "loop" and depth < _MAX_DEPTH:
            body_count = _count_steps(db, by_parent, by_parent.get(step.id, []), depth + 1)
            config = engine._loads(step.config, {}) or {}
            # count 模式次数已知按 体量×次数 估；list/while 运行前未知，估 1 轮
            if config.get("mode") == "count" and isinstance(config.get("count"), int):
                total += body_count * min(config["count"], engine.MAX_LOOP_ITERATIONS)
            else:
                total += body_count
    return total


@dataclass(frozen=True)
class _StepNode:
    """场景步骤的轻量快照（脱离 ORM/session）。

    执行期 `_record_step` 每步 commit 会因 expire_on_commit 让 ORM 步骤对象过期、
    下次访问属性时逐行补查——缓存 ORM 对象等于没缓存。故运行态只用本快照，
    一次 run 内步骤树查一次即冻结（运行中被并发编辑不热更新，语义更一致）。
    """

    id: int
    parent_step_id: Optional[int]
    type: str
    enabled: bool
    ref_case_id: Optional[int]
    ref_scenario_id: Optional[int]
    wait_ms: Optional[int]
    config: Optional[str]
    name: Optional[str]


def _snapshot_step_tree(db: Session, scenario_id: int) -> Dict[Optional[int], List[_StepNode]]:
    """一次查询取全部步骤，按 parent 分桶为快照（属性即取即存，不受后续 commit 过期影响）。"""
    by_parent: Dict[Optional[int], List[_StepNode]] = defaultdict(list)
    for s in scenario_repo.list_steps(db, scenario_id):
        by_parent[s.parent_step_id].append(_StepNode(
            id=s.id, parent_step_id=s.parent_step_id, type=s.type, enabled=s.enabled,
            ref_case_id=s.ref_case_id, ref_scenario_id=s.ref_scenario_id,
            wait_ms=s.wait_ms, config=s.config, name=s.name,
        ))
    return by_parent


class _RunContext:
    """一次运行的共享状态（run 行、计数、runtime 变量、当前 step 序号）。"""

    def __init__(self, db: Session, run: ApifoxRun, environment: Optional[ApifoxEnvironment],
                 user_id: Optional[int]):
        self.db = db
        self.run = run
        self.environment = environment
        self.user_id = user_id
        self.runtime: Dict[str, str] = {}
        self.index = 0
        self.passed = 0
        self.failed = 0
        self.iteration = 0  # 数据驱动/循环当前轮次（0 基），落到每个步骤供报告分组
        # 步骤树按 scenario_id 记忆化为快照：数据驱动/循环多轮不再每轮重查步骤表（评审 #4）
        self.step_tree_cache: Dict[int, Dict[Optional[int], List[_StepNode]]] = {}
        # 登录态跨步骤透传（仅场景开启）：共享 cookie jar + 传递中的 token
        self.propagate_auth = False
        self.cookie_jar = httpx.Cookies()
        self.auth_token: Optional[str] = None

    def reset_auth_state(self) -> None:
        """每轮迭代（数据驱动/循环）重置登录态，各轮互不串。"""
        self.cookie_jar = httpx.Cookies()
        self.auth_token = None

    def propagation_kwargs(self) -> Dict[str, Any]:
        if not self.propagate_auth:
            return {}
        return {"cookie_jar": self.cookie_jar, "auth_token": self.auth_token}

    def absorb_captured_token(self, detail: Dict[str, Any]) -> None:
        if self.propagate_auth and detail.get("captured_token"):
            self.auth_token = detail["captured_token"]


def _record_step(ctx: _RunContext, step_type: str, status: str, detail: Dict[str, Any],
                 case: Optional[ApifoxEndpointCase] = None, case_name: str = "",
                 depth: int = 0) -> ApifoxRunStep:
    step = ApifoxRunStep(
        run_id=ctx.run.id,
        step_type=step_type,
        depth=depth,
        iteration=ctx.iteration,
        case_id=case.id if case else None,
        case_name=case_name or (case.name if case else ""),
        method=detail.get("method") or "",
        url=detail.get("url") or "",
        status=status,
        duration_ms=detail.get("duration_ms"),
        response_status=detail.get("response_status"),
        request_headers=_dumps(detail.get("request_headers") or {}),
        request_body=detail.get("request_body") or "",
        response_headers=_dumps(detail.get("response_headers") or {}),
        response_body=detail.get("response_body") or "",
        assertion_results=_dumps(detail.get("assertion_results") or []),
        extract_results=_dumps(detail.get("extract_results") or []),
        script_logs=_dumps(detail.get("script_logs") or []),
        contract_result=_dumps(detail["contract_result"]) if detail.get("contract_result") else None,
        warnings=_dumps(detail.get("warnings") or []),
        error_message=detail.get("error_message"),
    )
    run_repo.add(ctx.db, step)
    ctx.db.commit()
    return step


def _step_event(ctx: _RunContext, total: int, status: str, detail: Dict[str, Any], case_name: str) -> Dict[str, Any]:
    return {
        "type": "step",
        "index": ctx.index,
        "total": total,
        "iteration": ctx.iteration,
        "case_name": case_name,
        "method": detail.get("method") or "",
        "status": status,
        "duration_ms": detail.get("duration_ms"),
        "response_status": detail.get("response_status"),
        "error_message": detail.get("error_message"),
    }


def _run_case_block(
    ctx: _RunContext, case: ApifoxEndpointCase, total: int,
    env_vars: Dict[str, str], global_vars: Dict[str, str], depth: int = 0,
) -> Generator[Dict[str, Any], None, None]:
    """执行一个用例（含数据驱动多迭代），落库并 yield step 事件。"""
    endpoint = endpoint_repo.get_endpoint(ctx.db, case.endpoint_id)
    assertions = case_repo.list_assertions(ctx.db, case.id)
    extracts = case_repo.list_extracts(ctx.db, case.id)
    case_vars = engine.case_variable_rows(case)

    for drive_row in engine.data_drive_rows(case, ctx.db):
        ctx.index += 1
        merged = engine.merge_vars(global_vars, env_vars, ctx.runtime, case_vars, drive_row or {})
        status: str
        detail: Dict[str, Any]
        if endpoint is None:
            status, detail = "failed", {"error_message": "用例所属接口不存在", "method": "", "url": ""}
        else:
            status, detail = engine.execute_case(
                ctx.db, case, endpoint, ctx.environment, merged, assertions, extracts,
                **ctx.propagation_kwargs(),
            )
        ctx.absorb_captured_token(detail)
        ctx.runtime.update(detail.get("extracted") or {})
        if detail.get("scoped"):
            engine.persist_scoped_extracts(
                ctx.db, ctx.run.project_id,
                ctx.environment.id if ctx.environment else None,
                ctx.user_id, detail["scoped"],
            )
        if status == "passed":
            ctx.passed += 1
        else:
            ctx.failed += 1
        name = case.name if not drive_row else f"{case.name} · 数据集{ctx.index}"
        _record_step(ctx, "case", status, detail, case=case, case_name=name, depth=depth)
        yield _step_event(ctx, total, status, detail, name)


def _extract_db_row(
    config: Dict[str, Any], first_row: Dict[str, Any], ctx: _RunContext
) -> tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """按提取配置从结果首行取列到变量；返回 (extract_results, scoped)。"""
    extract_results: List[Dict[str, Any]] = []
    scoped: List[Dict[str, str]] = []
    for ex in config.get("extracts") or []:
        var_name = str(ex.get("var_name") or "").strip()
        column = str(ex.get("column") or "").strip()
        scope = ex.get("scope") or "temporary"
        if not var_name or not column:
            continue
        if column in first_row:
            raw = first_row[column]
            value = "" if raw is None else str(raw)
            ctx.runtime[var_name] = value
            extract_results.append({"var_name": var_name, "column": column, "scope": scope,
                                    "passed": True, "value": value, "message": ""})
            if scope in ("environment", "global"):
                scoped.append({"key": var_name, "value": value, "scope": scope})
        else:
            extract_results.append({"var_name": var_name, "column": column, "scope": scope,
                                    "passed": False, "value": "", "message": f"结果集无列「{column}」"})
    return extract_results, scoped


def _run_db_step(
    ctx: _RunContext, step: _StepNode, total: int,
    env_vars: Dict[str, str], global_vars: Dict[str, str], depth: int,
) -> Generator[Dict[str, Any], None, None]:
    """数据库操作步骤：解析连接(须属当前环境)→{{var}}插值 SQL→执行→首行提取变量→落库。"""
    ctx.index += 1
    config = engine._loads(step.config, {}) or {}
    label = step.name or "数据库操作"
    merged = engine.merge_vars(global_vars, env_vars, ctx.runtime)
    sql = engine.apply_vars(config.get("sql") or "", merged)

    conn = None
    if ctx.environment and config.get("connection_id"):
        try:  # 防旧脏数据/绕过保存校验的非法 connection_id 抛异常卡 running
            conn_id = int(config["connection_id"])
        except (TypeError, ValueError):
            conn_id = None
        if conn_id is not None:
            candidate = database_conn_repo.get(ctx.db, conn_id)
            if candidate and candidate.environment_id == ctx.environment.id:
                conn = candidate

    if conn is None:
        detail = {"method": "SQL", "url": "", "request_body": sql, "duration_ms": 0.0,
                  "error_message": "数据库连接不存在或不属于当前环境（需先配置连接并选中环境）"}
        ctx.failed += 1
        _record_step(ctx, "db", "failed", detail, case_name=label, depth=depth)
        yield _step_event(ctx, total, "failed", detail, label)
        return

    started = time.perf_counter()
    result = db_executor.run_sql(conn, sql)
    duration_ms = (time.perf_counter() - started) * 1000

    extract_results: List[Dict[str, Any]] = []
    scoped: List[Dict[str, str]] = []
    if result["passed"]:
        first_row = result["rows"][0] if result["rows"] else {}
        extract_results, scoped = _extract_db_row(config, first_row, ctx)

    status = "passed" if result["passed"] else "failed"
    detail = {
        "method": "SQL", "url": conn.name, "duration_ms": duration_ms,
        "request_body": sql,
        "response_body": _dumps({"columns": result["columns"], "rows": result["rows"],
                                 "rowcount": result["rowcount"]}),
        "extract_results": extract_results,
        "error_message": result.get("error"),
    }
    if scoped:
        engine.persist_scoped_extracts(
            ctx.db, ctx.run.project_id,
            ctx.environment.id if ctx.environment else None, ctx.user_id, scoped,
        )
    if status == "passed":
        ctx.passed += 1
    else:
        ctx.failed += 1
    _record_step(ctx, "db", status, detail, case_name=label, depth=depth)
    yield _step_event(ctx, total, status, detail, label)


def _run_http_step(
    ctx: _RunContext, step: _StepNode, total: int,
    env_vars: Dict[str, str], global_vars: Dict[str, str], depth: int,
) -> Generator[Dict[str, Any], None, None]:
    """裸 HTTP 请求步骤：config 自带 method/path/request_spec/断言/提取，{{var}}插值后发送并落库。"""
    ctx.index += 1
    config = engine._loads(step.config, {}) or {}
    label = step.name or config.get("name") or f"{config.get('method') or 'GET'} {config.get('path') or ''}".strip()
    merged = engine.merge_vars(global_vars, env_vars, ctx.runtime)
    try:  # 脏数据/绕过校验的非法断言/提取行不得抛异常冒泡卡 run 于 running
        assertions = [AssertionRow(**a) for a in config.get("assertions") or []]
        extracts = [ExtractRow(**e) for e in config.get("extracts") or []]
    except (ValidationError, TypeError) as exc:
        detail = {"method": config.get("method") or "", "url": config.get("path") or "",
                  "duration_ms": 0.0, "error_message": f"HTTP 步骤断言/提取配置无效: {exc}"}
        ctx.failed += 1
        _record_step(ctx, "http", "failed", detail, case_name=label, depth=depth)
        yield _step_event(ctx, total, "failed", detail, label)
        return
    status, detail = engine.execute_http_request(
        ctx.db, ctx.run.project_id, config.get("method") or "GET", config.get("path") or "",
        config.get("server_name"), config.get("request_spec") or {}, assertions, extracts,
        ctx.environment, merged, **ctx.propagation_kwargs(),
    )
    ctx.absorb_captured_token(detail)
    ctx.runtime.update(detail.get("extracted") or {})
    if detail.get("scoped"):
        engine.persist_scoped_extracts(
            ctx.db, ctx.run.project_id,
            ctx.environment.id if ctx.environment else None, ctx.user_id, detail["scoped"],
        )
    if status == "passed":
        ctx.passed += 1
    else:
        ctx.failed += 1
    _record_step(ctx, "http", status, detail, case_name=label, depth=depth)
    yield _step_event(ctx, total, status, detail, label)


def _run_scenario_block(
    ctx: _RunContext, scenario_id: int, total: int,
    env_vars: Dict[str, str], global_vars: Dict[str, str], depth: int = 0,
) -> Generator[Dict[str, Any], None, None]:
    if depth > _MAX_DEPTH:
        return
    by_parent = ctx.step_tree_cache.get(scenario_id)
    if by_parent is None:
        by_parent = _snapshot_step_tree(ctx.db, scenario_id)
        ctx.step_tree_cache[scenario_id] = by_parent
    yield from _run_steps(ctx, by_parent, by_parent.get(None, []), total, env_vars, global_vars, depth)


def _run_steps(
    ctx: _RunContext, by_parent: Dict[Optional[int], List[_StepNode]],
    steps: List[_StepNode], total: int,
    env_vars: Dict[str, str], global_vars: Dict[str, str], depth: int,
) -> Generator[Dict[str, Any], None, None]:
    """按序执行一层步骤；控制步骤(group)递归其子步骤，深度 +1（供报告缩进）。"""
    for step in steps:
        if not step.enabled:
            continue
        if step.type == "case" and step.ref_case_id:
            case = case_repo.get_case(ctx.db, step.ref_case_id)
            if case:
                yield from _run_case_block(ctx, case, total, env_vars, global_vars, depth)
        elif step.type == "wait":
            ctx.index += 1
            wait_ms = min(step.wait_ms or 0, MAX_WAIT_MS)
            time.sleep(wait_ms / 1000)
            detail = {"method": "", "url": "", "duration_ms": float(wait_ms)}
            ctx.passed += 1
            _record_step(ctx, "wait", "passed", detail, case_name=f"等待 {wait_ms} ms", depth=depth)
            yield _step_event(ctx, total, "passed", detail, f"等待 {wait_ms} ms")
        elif step.type in ("break", "continue"):
            ctx.index += 1
            label = step.name or ("跳出循环" if step.type == "break" else "跳过本轮")
            detail = {"method": "", "url": "", "duration_ms": 0.0}
            ctx.passed += 1
            _record_step(ctx, step.type, "passed", detail, case_name=label, depth=depth)
            yield _step_event(ctx, total, "passed", detail, label)
            raise _BreakLoop() if step.type == "break" else _ContinueLoop()
        elif step.type == "scenario" and step.ref_scenario_id:
            yield from _run_scenario_block(
                ctx, step.ref_scenario_id, total, env_vars, global_vars, depth + 1
            )
        elif step.type == "group" and depth < _MAX_DEPTH:
            yield from _run_steps(
                ctx, by_parent, by_parent.get(step.id, []), total, env_vars, global_vars, depth + 1
            )
        elif step.type == "if" and depth < _MAX_DEPTH:
            yield from _run_if_block(ctx, by_parent, step, total, env_vars, global_vars, depth)
        elif step.type == "loop" and depth < _MAX_DEPTH:
            yield from _run_loop_block(ctx, by_parent, step, total, env_vars, global_vars, depth)
        elif step.type == "db":
            yield from _run_db_step(ctx, step, total, env_vars, global_vars, depth)
        elif step.type == "http":
            yield from _run_http_step(ctx, step, total, env_vars, global_vars, depth)


def _run_loop_block(
    ctx: _RunContext, by_parent: Dict[Optional[int], List[_StepNode]],
    step: _StepNode, total: int,
    env_vars: Dict[str, str], global_vars: Dict[str, str], depth: int,
) -> Generator[Dict[str, Any], None, None]:
    """循环步骤：按模式跑循环体（depth+1）。count/list 预算迭代序列并逐轮注入循环变量；
    while 逐轮重求条件；三模式都受 MAX_LOOP_ITERATIONS 硬上限兜底。循环变量写 ctx.runtime。"""
    config = engine._loads(step.config, {}) or {}
    body = by_parent.get(step.id, [])
    if config.get("mode") == "while":
        condition = config.get("condition") or {}
        try:
            max_iter = min(int(config.get("max_iterations") or 0), engine.MAX_LOOP_ITERATIONS)
        except (TypeError, ValueError):
            max_iter = 0
        n = 0
        while n < max_iter:
            cond_vars = engine.merge_vars(global_vars, env_vars, ctx.runtime)
            passed, _msg = engine.evaluate_condition(condition, cond_vars)
            if not passed:
                break
            n += 1
            try:
                yield from _run_steps(ctx, by_parent, body, total, env_vars, global_vars, depth + 1)
            except _ContinueLoop:
                continue
            except _BreakLoop:
                break
        return
    # 循环变量(index/item)按 loop 层级作用域：进入前快照、退出后恢复，
    # 避免嵌套同名循环变量互相污染（内层跑完不该把 index 残留给外层后续步骤）
    scoped = {str(config.get("index_var") or "index")}
    if config.get("mode") == "list":
        scoped.add(str(config.get("item_var") or "item"))
    saved = {k: ctx.runtime[k] for k in scoped if k in ctx.runtime}
    entry_vars = engine.merge_vars(global_vars, env_vars, ctx.runtime)
    try:
        for injection in engine.loop_iterations(config, entry_vars):
            ctx.runtime.update(injection)
            try:
                yield from _run_steps(ctx, by_parent, body, total, env_vars, global_vars, depth + 1)
            except _ContinueLoop:
                continue
            except _BreakLoop:
                break
    finally:
        for k in scoped:
            if k in saved:
                ctx.runtime[k] = saved[k]
            else:
                ctx.runtime.pop(k, None)


def _run_if_block(
    ctx: _RunContext, by_parent: Dict[Optional[int], List[_StepNode]],
    step: _StepNode, total: int,
    env_vars: Dict[str, str], global_vars: Dict[str, str], depth: int,
) -> Generator[Dict[str, Any], None, None]:
    """条件步骤：对当前变量求值，命中 then 分支或 else 分支（未命中分支不执行不落库）。

    then 分支 = if 的非 else 子步骤；else 分支 = else 子容器的子步骤（else 透明不额外加深度）。
    """
    children = by_parent.get(step.id, [])
    condition = (engine._loads(step.config, {}) or {}).get("condition") or {}
    cond_vars = engine.merge_vars(global_vars, env_vars, ctx.runtime)
    passed, _msg = engine.evaluate_condition(condition, cond_vars)
    if passed:
        branch = [c for c in children if c.type != "else"]
    else:
        else_step = next((c for c in children if c.type == "else" and c.enabled), None)
        branch = by_parent.get(else_step.id, []) if else_step else []
    yield from _run_steps(ctx, by_parent, branch, total, env_vars, global_vars, depth + 1)


def recover_orphan_runs(db: Session) -> None:
    """启动回收：卡在 running 的运行必是上次进程中途被杀残留（SSE 运行不跨重启），标记为失败。"""
    n = run_repo.mark_running_interrupted(db)
    if n:
        db.commit()
        logger.info("启动回收：%s 个残留 running 运行标记为失败", n)


def _start_run(db: Session, project_id: int, target_type: str, target_id: int,
               target_name: str, environment: Optional[ApifoxEnvironment],
               triggered_by: str, total: int, parent_run_id: Optional[int] = None) -> ApifoxRun:
    run = ApifoxRun(
        project_id=project_id,
        parent_run_id=parent_run_id,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        environment_id=environment.id if environment else None,
        status="running",
        total_count=total,
        triggered_by=triggered_by,
        started_at=datetime.utcnow(),
    )
    run_repo.add(db, run)
    db.commit()
    db.refresh(run)
    return run


def _notify_run_failure(db: Session, run: ApifoxRun) -> None:
    """执行失败通知。子运行（有父）不单独通知；定时触发由 schedule_service 通知，避免重复。"""
    if run.parent_run_id is not None or (run.triggered_by or "").startswith("schedule:"):
        return
    from app.services.apifox import notify_service  # 延迟导入避免顶层循环

    try:
        total = (run.passed_count or 0) + (run.failed_count or 0)
        detail = (
            f"{run.target_type}「{run.target_name}」执行失败："
            f"{run.failed_count}/{total} 失败。运行记录 #{run.id}。"
        )
        notify_service.notify_failure(db, run.project_id, "run", f"执行失败：{run.target_name}", detail)
    except Exception:  # noqa: BLE001 - 通知不影响主流程
        logger.exception("执行失败通知异常 run=%s", run.id)


def _finalize(ctx: _RunContext, started: float) -> Dict[str, Any]:
    run = ctx.run
    run.passed_count = ctx.passed
    run.failed_count = ctx.failed
    run.status = "passed" if ctx.failed == 0 else "failed"
    run.duration_ms = (time.perf_counter() - started) * 1000
    run.pass_rate = round(ctx.passed / ctx.index * 100, 2) if ctx.index else 0.0
    run.finished_at = datetime.utcnow()
    ctx.db.commit()
    if run.status == "failed":
        _notify_run_failure(ctx.db, run)
    return {
        "type": "done",
        "run_id": run.id,
        "status": run.status,
        "passed_count": run.passed_count,
        "failed_count": run.failed_count,
        "pass_rate": run.pass_rate,
        "duration_ms": run.duration_ms,
        "message": "执行完成",
    }


def iter_case_run(
    db: Session, case: ApifoxEndpointCase, environment: Optional[ApifoxEnvironment],
    triggered_by: str, user_id: Optional[int], parent_run_id: Optional[int] = None,
) -> Generator[Dict[str, Any], None, None]:
    total = _count_case_steps(db, case)
    run = _start_run(db, case.project_id, "case", case.id, case.name, environment, triggered_by,
                     total, parent_run_id)
    yield {"type": "start", "run_id": run.id, "total": total, "message": f"开始执行用例「{case.name}」"}

    ctx = _RunContext(db, run, environment, user_id)
    env_vars = engine.resolve_env_vars(db, environment.id if environment else None, user_id)
    global_vars = engine.resolve_global_vars(db, case.project_id, user_id)
    started = time.perf_counter()
    yield from _run_case_block(ctx, case, total, env_vars, global_vars)
    yield _finalize(ctx, started)


def _resolve_scenario_iterations(db: Session, scenario: ApifoxScenario) -> List[Dict[str, str]]:
    """场景运行配置 → 外层迭代列表。

    绑数据集：每个 enabled 行一组注入变量（整场景各跑一遍）；数据集缺失/空/异常降级为单次空注入。
    未绑数据集：按 loop_count 跑 N 遍（无注入，MAX_LOOP_ITERATIONS 硬上限防误配爆量）。
    """
    config = engine._loads(scenario.run_config, {}) or {}
    dataset_id = config.get("dataset_id")
    if dataset_id:
        try:
            dsid = int(dataset_id)
        except (TypeError, ValueError):
            return [{}]
        dataset = dataset_repo.get_dataset(db, dsid)
        if dataset and dataset.project_id == scenario.project_id:
            injections: List[Dict[str, str]] = []
            for row in dataset_repo.list_rows(db, dataset.id):
                if row.enabled is False:
                    continue
                values = engine._loads(row.values, {}) or {}
                injections.append({str(k): "" if v is None else str(v) for k, v in values.items()})
            if injections:
                return injections
        return [{}]
    try:
        n = int(config.get("loop_count") or 1)
    except (TypeError, ValueError):
        n = 1
    n = max(1, min(n, engine.MAX_LOOP_ITERATIONS))
    return [{} for _ in range(n)]


def iter_scenario_run(
    db: Session, scenario: ApifoxScenario, environment: Optional[ApifoxEnvironment],
    triggered_by: str, user_id: Optional[int], parent_run_id: Optional[int] = None,
) -> Generator[Dict[str, Any], None, None]:
    iterations = _resolve_scenario_iterations(db, scenario)
    total = _count_scenario_steps(db, scenario.id) * len(iterations)
    run = _start_run(
        db, scenario.project_id, "scenario", scenario.id, scenario.name, environment, triggered_by,
        total, parent_run_id,
    )
    # 多轮（数据驱动/循环）才落 meta：单轮运行报告不分组，零视觉变化
    multi = len(iterations) > 1
    if multi:
        run.iterations_meta = _dumps(iterations)
        db.commit()
    start_event = {"type": "start", "run_id": run.id, "total": total,
                   "message": f"开始执行场景「{scenario.name}」"}
    if multi:
        start_event["iterations"] = iterations
    yield start_event

    ctx = _RunContext(db, run, environment, user_id)
    # 登录态跨步骤透传：run_config 缺字段时默认开（存量场景亦生效）
    ctx.propagate_auth = bool((engine._loads(scenario.run_config, {}) or {}).get("propagate_auth", True))
    env_vars = engine.resolve_env_vars(db, environment.id if environment else None, user_id)
    global_vars = engine.resolve_global_vars(db, scenario.project_id, user_id)
    started = time.perf_counter()
    try:
        for i, injection in enumerate(iterations):
            ctx.iteration = i
            # 每组数据独立 runtime：数据集行/循环各轮变量互不串（对齐用例数据驱动语义）
            ctx.runtime = dict(injection)
            ctx.reset_auth_state()  # 每轮独立登录态，与 runtime 同步隔离
            try:
                yield from _run_scenario_block(ctx, scenario.id, total, env_vars, global_vars)
            except (_BreakLoop, _ContinueLoop):
                pass  # 循环外的 break/continue（保存校验应已拦截），防御性忽略以正常收尾
    except Exception:
        _fail_orphan_run(db, run.id)  # 迭代中途未预期异常：兜底写失败态，避免永久卡 running
        raise
    yield _finalize(ctx, started)


def _resolve_suite_item(
    db: Session, item: ApifoxSuiteItem, environment: Optional[ApifoxEnvironment],
    triggered_by: str, user_id: Optional[int], parent_run_id: int,
):
    """把套件项解析为 (展示名, 子运行生成器)；目标已删除时生成器为 None。"""
    if item.target_type == "case":
        case = case_repo.get_case(db, item.target_id)
        if not case:
            return "(用例已删除)", None
        return case.name, iter_case_run(db, case, environment, triggered_by, user_id, parent_run_id)
    scenario = scenario_repo.get_scenario(db, item.target_id)
    if not scenario:
        return "(场景已删除)", None
    return scenario.name, iter_scenario_run(
        db, scenario, environment, triggered_by, user_id, parent_run_id
    )


def _fail_orphan_run(db: Session, run_id: Optional[int]) -> None:
    """子运行执行中途异常退出，未走到 finalize：兜底写失败态，避免永久卡 running。"""
    if not run_id:
        return
    orphan = run_repo.get_run(db, run_id)
    if orphan and orphan.status == "running":
        orphan.status = "failed"
        orphan.finished_at = datetime.utcnow()
        db.commit()


def _finalize_suite(db: Session, run: ApifoxRun, started: float,
                    passed_items: int, failed_items: int) -> Dict[str, Any]:
    run.passed_count = passed_items
    run.failed_count = failed_items
    run.status = "passed" if failed_items == 0 else "failed"
    run.duration_ms = (time.perf_counter() - started) * 1000
    done = passed_items + failed_items
    run.pass_rate = round(passed_items / done * 100, 2) if done else 0.0
    run.finished_at = datetime.utcnow()
    db.commit()
    if run.status == "failed":
        _notify_run_failure(db, run)
    return {
        "type": "suite_done",
        "run_id": run.id,
        "status": run.status,
        "passed_count": passed_items,
        "failed_count": failed_items,
        "pass_rate": run.pass_rate,
        "duration_ms": run.duration_ms,
        "message": "套件执行完成",
    }


def iter_suite_run(
    db: Session, suite: ApifoxSuite, environment: Optional[ApifoxEnvironment],
    triggered_by: str, user_id: Optional[int],
) -> Generator[Dict[str, Any], None, None]:
    """套件运行：父运行聚合 + 每项(用例/场景)各自独立子运行(fresh runtime，互不串变量)。

    统计为 item 级（子运行 passed 即该项通过）；单项失败隔离，不中断后续项。
    """
    items = [it for it in suite_repo.list_items(db, suite.id) if it.enabled]
    total = len(items)
    run = _start_run(db, suite.project_id, "suite", suite.id, suite.name, environment, triggered_by, total)
    yield {"type": "suite_start", "run_id": run.id, "total": total,
           "message": f"开始执行套件「{suite.name}」"}

    started = time.perf_counter()
    passed_items = 0
    failed_items = 0
    finalized = False
    try:
        for index, item in enumerate(items, start=1):
            item_status = "failed"
            child_run_id: Optional[int] = None
            target_name = ""
            try:
                target_name, child_gen = _resolve_suite_item(
                    db, item, environment, triggered_by, user_id, run.id
                )
                yield {"type": "item_start", "index": index, "total": total,
                       "target_type": item.target_type, "target_id": item.target_id,
                       "target_name": target_name}
                if child_gen is None:
                    yield {"type": "item_done", "index": index, "total": total,
                           "target_name": target_name, "status": "failed", "child_run_id": None,
                           "error_message": "套件项引用的目标已不存在"}
                else:
                    for ev in child_gen:
                        etype = ev.get("type")
                        if etype == "start":
                            child_run_id = ev.get("run_id")
                        elif etype == "step":
                            yield {**ev, "item_index": index}  # 转发子步骤，附 item 上下文供前端归组
                        elif etype == "done":
                            item_status = ev.get("status") or "failed"
                            yield {"type": "item_done", "index": index, "total": total,
                                   "target_name": target_name, "status": item_status,
                                   "child_run_id": ev.get("run_id"),
                                   "passed_count": ev.get("passed_count"),
                                   "failed_count": ev.get("failed_count"),
                                   "duration_ms": ev.get("duration_ms")}
            except Exception as exc:  # noqa: BLE001 - 单项失败隔离，不中断后续项
                # 子运行 commit 失败会让 session 进入需 rollback 才能续用的状态；
                # 不先回滚，下一项及兜底的 commit 都会连锁 PendingRollbackError。
                db.rollback()
                _fail_orphan_run(db, child_run_id)
                item_status = "failed"
                yield {"type": "item_done", "index": index, "total": total,
                       "target_name": target_name, "status": "failed", "child_run_id": child_run_id,
                       "error_message": f"套件项执行失败: {exc}"}
            if item_status == "passed":
                passed_items += 1
            else:
                failed_items += 1
        yield _finalize_suite(db, run, started, passed_items, failed_items)
        finalized = True
    finally:
        # 兜底：任何中途异常逃逸（如 finalize 本身失败）都不让父运行永久卡 running
        if not finalized:
            try:
                db.rollback()
            except Exception:  # noqa: BLE001
                pass
            _fail_orphan_run(db, run.id)

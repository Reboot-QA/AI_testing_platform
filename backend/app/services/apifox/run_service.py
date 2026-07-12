"""Apifox 执行引擎 · 编排层（SSE 生成器：建 run → 逐步执行落库 yield → 收尾统计）。

事件契约沿旧模块：start / step / done / error（error 由路由层兜底转换）。
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.run import ApifoxRun, ApifoxRunStep
from app.models.apifox.scenario import ApifoxScenario, ApifoxScenarioStep
from app.models.apifox.variable import ApifoxEnvironment
from app.repositories.apifox import case_repo, endpoint_repo, run_repo, scenario_repo
from app.services.apifox import run_engine as engine

MAX_WAIT_MS = 60000
_MAX_DEPTH = 50


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _count_case_steps(case: ApifoxEndpointCase) -> int:
    return len(engine.data_drive_rows(case))


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
                total += _count_case_steps(case)
        elif step.type == "wait":
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
    return total


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


def _record_step(ctx: _RunContext, step_type: str, status: str, detail: Dict[str, Any],
                 case: Optional[ApifoxEndpointCase] = None, case_name: str = "",
                 depth: int = 0) -> ApifoxRunStep:
    step = ApifoxRunStep(
        run_id=ctx.run.id,
        step_type=step_type,
        depth=depth,
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

    for drive_row in engine.data_drive_rows(case):
        ctx.index += 1
        merged = engine.merge_vars(global_vars, env_vars, ctx.runtime, case_vars, drive_row or {})
        status: str
        detail: Dict[str, Any]
        if endpoint is None:
            status, detail = "failed", {"error_message": "用例所属接口不存在", "method": "", "url": ""}
        else:
            status, detail = engine.execute_case(
                ctx.db, case, endpoint, ctx.environment, merged, assertions, extracts
            )
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


def _run_scenario_block(
    ctx: _RunContext, scenario_id: int, total: int,
    env_vars: Dict[str, str], global_vars: Dict[str, str], depth: int = 0,
) -> Generator[Dict[str, Any], None, None]:
    if depth > _MAX_DEPTH:
        return
    by_parent = scenario_repo.group_steps_by_parent(ctx.db, scenario_id)
    yield from _run_steps(ctx, by_parent, by_parent.get(None, []), total, env_vars, global_vars, depth)


def _run_steps(
    ctx: _RunContext, by_parent: Dict[Optional[int], List[ApifoxScenarioStep]],
    steps: List[ApifoxScenarioStep], total: int,
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


def _run_if_block(
    ctx: _RunContext, by_parent: Dict[Optional[int], List[ApifoxScenarioStep]],
    step: ApifoxScenarioStep, total: int,
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


def _start_run(db: Session, project_id: int, target_type: str, target_id: int,
               target_name: str, environment: Optional[ApifoxEnvironment],
               triggered_by: str, total: int) -> ApifoxRun:
    run = ApifoxRun(
        project_id=project_id,
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


def _finalize(ctx: _RunContext, started: float) -> Dict[str, Any]:
    run = ctx.run
    run.passed_count = ctx.passed
    run.failed_count = ctx.failed
    run.status = "passed" if ctx.failed == 0 else "failed"
    run.duration_ms = (time.perf_counter() - started) * 1000
    run.pass_rate = round(ctx.passed / ctx.index * 100, 2) if ctx.index else 0.0
    run.finished_at = datetime.utcnow()
    ctx.db.commit()
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
    triggered_by: str, user_id: Optional[int],
) -> Generator[Dict[str, Any], None, None]:
    total = _count_case_steps(case)
    run = _start_run(db, case.project_id, "case", case.id, case.name, environment, triggered_by, total)
    yield {"type": "start", "run_id": run.id, "total": total, "message": f"开始执行用例「{case.name}」"}

    ctx = _RunContext(db, run, environment, user_id)
    env_vars = engine.resolve_env_vars(db, environment.id if environment else None, user_id)
    global_vars = engine.resolve_global_vars(db, case.project_id, user_id)
    started = time.perf_counter()
    yield from _run_case_block(ctx, case, total, env_vars, global_vars)
    yield _finalize(ctx, started)


def iter_scenario_run(
    db: Session, scenario: ApifoxScenario, environment: Optional[ApifoxEnvironment],
    triggered_by: str, user_id: Optional[int],
) -> Generator[Dict[str, Any], None, None]:
    total = _count_scenario_steps(db, scenario.id)
    run = _start_run(
        db, scenario.project_id, "scenario", scenario.id, scenario.name, environment, triggered_by, total
    )
    yield {"type": "start", "run_id": run.id, "total": total, "message": f"开始执行场景「{scenario.name}」"}

    ctx = _RunContext(db, run, environment, user_id)
    env_vars = engine.resolve_env_vars(db, environment.id if environment else None, user_id)
    global_vars = engine.resolve_global_vars(db, scenario.project_id, user_id)
    started = time.perf_counter()
    yield from _run_scenario_block(ctx, scenario.id, total, env_vars, global_vars)
    yield _finalize(ctx, started)

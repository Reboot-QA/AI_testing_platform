"""Apifox 定时任务 · 业务层。

复用旧调度线程（不新起调度器）：只写 next_run_at 参与轮询，到期由线程扫描执行。
调度算法/校验/描述直接复用旧 schedule_service 的鸭子类型函数（只读 schedule_type/
run_time/week_day/interval_minutes/last_run_at 属性）。定时执行 user_id=None（只读远程值、
提取写远程值，见 run_engine）。
"""

import logging
from datetime import datetime
from typing import Any, Optional, cast

from sqlalchemy.orm import Session

from app.models.apifox.schedule import ApifoxSchedule
from app.repositories.apifox import (
    case_repo,
    scenario_repo,
    schedule_repo,
    variable_repo,
)
from app.services.apifox import run_service
from app.services.schedule_service import (
    compute_next_run_at,
    format_schedule_desc,
    validate_schedule_fields,
)
from app.utils.time_util import now_local

logger = logging.getLogger(__name__)

TARGET_TYPES = {"case", "scenario"}

# 复用旧调度函数（鸭子类型：只读 schedule_type/run_time/week_day/interval_minutes/last_run_at）；
# 薄封装并 cast，让类型系统接受 ApifoxSchedule，同时对路由屏蔽底层来源。
validate_fields = validate_schedule_fields


def describe(task: ApifoxSchedule) -> str:
    return format_schedule_desc(cast(Any, task))


def _compute_next(task: ApifoxSchedule, from_dt: Optional[datetime] = None) -> datetime:
    return compute_next_run_at(cast(Any, task), from_dt=from_dt)


def resolve_target_name(db: Session, target_type: str, target_id: int) -> Optional[str]:
    """校验目标存在并返回其名称；不存在返回 None。"""
    if target_type == "case":
        case = case_repo.get_case(db, target_id)
        return case.name if case else None
    if target_type == "scenario":
        scenario = scenario_repo.get_scenario(db, target_id)
        return scenario.name if scenario else None
    return None


def refresh_schedule(db: Session, task: ApifoxSchedule, *, force_from_now: bool = False) -> None:
    if task.enabled:
        base = now_local() if force_from_now else None
        task.next_run_at = _compute_next(task, from_dt=base)
    else:
        task.next_run_at = None
    db.commit()
    db.refresh(task)


def execute_schedule(db: Session, task: ApifoxSchedule) -> None:
    """定时执行体：完整消费执行生成器落库，回写 last_run_* 与 next_run_at。

    异常一律吞掉记 failed，避免拖垮轮询线程或其他任务。
    """
    try:
        environment = None
        if task.environment_id:
            environment = variable_repo.get_environment(db, task.environment_id)

        run_id: Optional[int] = None
        status = "failed"
        triggered_by = f"schedule:{task.name}"

        if task.target_type == "case":
            case = case_repo.get_case(db, task.target_id)
            events = (
                run_service.iter_case_run(db, case, environment, triggered_by, None)
                if case else None
            )
        elif task.target_type == "scenario":
            scenario = scenario_repo.get_scenario(db, task.target_id)
            events = (
                run_service.iter_scenario_run(db, scenario, environment, triggered_by, None)
                if scenario else None
            )
        else:
            events = None

        if events is None:
            logger.warning("apifox 定时任务 %s 目标缺失，跳过执行", task.id)
        else:
            for event in events:
                if event.get("run_id"):
                    run_id = event["run_id"]
                if event.get("type") == "done":
                    status = event.get("status") or "failed"

        task.last_run_at = now_local()
        task.last_run_id = run_id
        task.last_run_status = status
    except Exception:  # noqa: BLE001 - 定时执行异常不得中断轮询线程
        logger.exception("apifox 定时任务 %s 执行异常", task.id)
        task.last_run_at = now_local()
        task.last_run_status = "failed"
    finally:
        if task.enabled:
            task.next_run_at = _compute_next(task, from_dt=now_local())
        db.commit()


def run_due_apifox_tasks(db: Session) -> None:
    """轮询线程调用：执行所有到期的 apifox 定时任务。"""
    for task in schedule_repo.list_due(db, now_local()):
        execute_schedule(db, task)


__all__ = [
    "describe",
    "validate_fields",
    "resolve_target_name",
    "refresh_schedule",
    "execute_schedule",
    "run_due_apifox_tasks",
    "TARGET_TYPES",
]

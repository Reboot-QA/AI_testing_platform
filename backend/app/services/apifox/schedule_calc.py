"""Apifox 定时任务 · 调度算法（下次运行计算 / 字段校验 / 描述）。

迁移自老 schedule_service，改为 apifox 自有；duck-typed（只读 schedule_type/run_time/
week_day/interval_minutes/last_run_at），供 apifox schedule_service 复用。cron 分支在
schedule_service 里另行处理（croniter）。
"""

from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

from app.utils.time_util import now_local

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
SCHEDULE_TYPES = {"daily", "weekly", "interval"}
MIN_INTERVAL_MINUTES = 5


def _parse_run_time(run_time: Optional[str]) -> Tuple[int, int]:
    parts = (run_time or "09:00").strip().split(":")
    hour = int(parts[0]) if parts else 9
    minute = int(parts[1]) if len(parts) > 1 else 0
    return max(0, min(23, hour)), max(0, min(59, minute))


def format_schedule_desc(task: Any) -> str:
    if task.schedule_type == "daily":
        return f"每天 {task.run_time or '09:00'}"
    if task.schedule_type == "weekly":
        day = task.week_day if task.week_day is not None else 0
        day_label = WEEKDAY_LABELS[day] if 0 <= day <= 6 else "周一"
        return f"每{day_label} {task.run_time or '09:00'}"
    minutes = max(MIN_INTERVAL_MINUTES, task.interval_minutes or MIN_INTERVAL_MINUTES)
    return f"每 {minutes} 分钟"


def compute_next_run_at(task: Any, from_dt: Optional[datetime] = None) -> datetime:
    now = (from_dt or now_local()).replace(microsecond=0)
    hour, minute = _parse_run_time(task.run_time)

    if task.schedule_type == "interval":
        interval = max(MIN_INTERVAL_MINUTES, task.interval_minutes or MIN_INTERVAL_MINUTES)
        if task.last_run_at:
            base = task.last_run_at.replace(microsecond=0)
            candidate = base + timedelta(minutes=interval)
            return candidate if candidate > now else now + timedelta(minutes=interval)
        return now + timedelta(minutes=interval)

    if task.schedule_type == "weekly":
        target_weekday = task.week_day if task.week_day is not None else 0
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = (target_weekday - candidate.weekday()) % 7
        if days_ahead == 0 and candidate <= now:
            days_ahead = 7
        return candidate + timedelta(days=days_ahead)

    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def validate_schedule_fields(
    *,
    schedule_type: str,
    run_time: Optional[str] = None,
    week_day: Optional[int] = None,
    interval_minutes: Optional[int] = None,
) -> None:
    if schedule_type not in SCHEDULE_TYPES:
        raise ValueError("调度类型无效，支持 daily / weekly / interval")
    if schedule_type in {"daily", "weekly"}:
        _parse_run_time(run_time or "09:00")
    if schedule_type == "weekly" and week_day is not None and not (0 <= week_day <= 6):
        raise ValueError("week_day 必须在 0-6 之间（0=周一）")
    if schedule_type == "interval":
        minutes = interval_minutes or MIN_INTERVAL_MINUTES
        if minutes < MIN_INTERVAL_MINUTES:
            raise ValueError(f"间隔执行最少 {MIN_INTERVAL_MINUTES} 分钟")

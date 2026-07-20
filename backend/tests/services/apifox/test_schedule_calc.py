"""apifox 调度算法（迁自老 schedule_service）：下次运行/校验/描述/时间解析的等价类+边界。"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.services.apifox import schedule_calc as sc


def _task(**kw):
    base = {"schedule_type": "daily", "run_time": "09:00", "week_day": 0,
            "interval_minutes": 30, "last_run_at": None}
    base.update(kw)
    return SimpleNamespace(**base)


# ---------- compute_next_run_at ----------
def test_daily_past_time_goes_next_day():
    nxt = sc.compute_next_run_at(_task(schedule_type="daily"), from_dt=datetime(2026, 7, 15, 10, 0))
    assert nxt == datetime(2026, 7, 16, 9, 0)


def test_daily_before_time_same_day():
    nxt = sc.compute_next_run_at(_task(schedule_type="daily"), from_dt=datetime(2026, 7, 15, 8, 0))
    assert nxt == datetime(2026, 7, 15, 9, 0)


def test_weekly_days_ahead_positive():
    # 2026-07-15 周三，目标周一(week_day=0)
    nxt = sc.compute_next_run_at(_task(schedule_type="weekly", week_day=0), from_dt=datetime(2026, 7, 15, 10, 0))
    assert nxt == datetime(2026, 7, 20, 9, 0)


def test_weekly_same_weekday_past_time_goes_next_week():
    # 目标周三，基准周三且已过 9 点 → +7 天
    nxt = sc.compute_next_run_at(_task(schedule_type="weekly", week_day=2), from_dt=datetime(2026, 7, 15, 10, 0))
    assert nxt == datetime(2026, 7, 22, 9, 0)


def test_interval_without_last_run():
    nxt = sc.compute_next_run_at(_task(schedule_type="interval", interval_minutes=30), from_dt=datetime(2026, 7, 15, 10, 0))
    assert nxt == datetime(2026, 7, 15, 10, 30)


def test_interval_with_last_run_future_candidate():
    task = _task(schedule_type="interval", interval_minutes=30, last_run_at=datetime(2026, 7, 15, 10, 0))
    nxt = sc.compute_next_run_at(task, from_dt=datetime(2026, 7, 15, 10, 5))
    assert nxt == datetime(2026, 7, 15, 10, 30)  # base+间隔仍在未来


def test_interval_with_last_run_stale_candidate_falls_back_to_now():
    task = _task(schedule_type="interval", interval_minutes=30, last_run_at=datetime(2026, 7, 15, 9, 0))
    nxt = sc.compute_next_run_at(task, from_dt=datetime(2026, 7, 15, 10, 5))
    assert nxt == datetime(2026, 7, 15, 10, 35)  # base+间隔已过 → now+间隔


# ---------- _parse_run_time 越界钳制 ----------
@pytest.mark.parametrize("run_time,expected", [
    ("09:30", (9, 30)),
    ("25:70", (23, 59)),
    ("-1:-5", (0, 0)),
    ("", (9, 0)),
])
def test_parse_run_time_clamps(run_time, expected):
    assert sc._parse_run_time(run_time) == expected


# ---------- format_schedule_desc ----------
def test_format_desc_variants():
    assert sc.format_schedule_desc(_task(schedule_type="daily")) == "每天 09:00"
    assert sc.format_schedule_desc(_task(schedule_type="weekly", week_day=0)) == "每周一 09:00"
    assert sc.format_schedule_desc(_task(schedule_type="interval", interval_minutes=30)) == "每 30 分钟"


# ---------- validate_schedule_fields ----------
def test_validate_rejects_bad_type():
    with pytest.raises(ValueError):
        sc.validate_schedule_fields(schedule_type="hourly")


def test_validate_rejects_bad_weekday():
    with pytest.raises(ValueError):
        sc.validate_schedule_fields(schedule_type="weekly", week_day=7)


def test_validate_rejects_too_small_interval():
    with pytest.raises(ValueError):
        sc.validate_schedule_fields(schedule_type="interval", interval_minutes=3)


def test_validate_accepts_valid():
    sc.validate_schedule_fields(schedule_type="daily", run_time="09:00")  # 不抛即通过

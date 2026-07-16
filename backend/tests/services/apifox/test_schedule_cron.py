"""apifox 定时任务 cron 分支：校验 / 描述 / 下次运行计算，且非 cron 仍委托老逻辑。"""

from datetime import datetime
from types import SimpleNamespace

import pytest

# 先加载 scenario_service，避免 schedule_service→run_service→run_engine 的既有循环导入
import app.services.apifox.scenario_service  # noqa: F401
from app.models.apifox.schedule import ApifoxSchedule
from app.services.apifox import schedule_service


def _cron_task(expr):
    return SimpleNamespace(schedule_type="cron", cron_expr=expr)


def test_validate_fields_cron_valid_passes():
    schedule_service.validate_fields(schedule_type="cron", cron_expr="0 9 * * 1")  # 不抛异常即通过


@pytest.mark.parametrize("expr", ["", "   ", None, "not a cron"])
def test_validate_fields_cron_invalid_raises(expr):
    with pytest.raises(ValueError):
        schedule_service.validate_fields(schedule_type="cron", cron_expr=expr)


def test_describe_cron_shows_expression():
    assert schedule_service.describe(_cron_task("0 9 * * 1")) == "Cron：0 9 * * 1"


def test_compute_next_cron_from_given_base():
    # 每周一 09:00；基准周三 10:00 → 下个周一 09:00
    nxt = schedule_service._compute_next(_cron_task("0 9 * * 1"), from_dt=datetime(2026, 7, 15, 10, 0))

    assert nxt == datetime(2026, 7, 20, 9, 0)


def test_compute_next_non_cron_delegates_to_legacy():
    # daily 09:00，基准 07-15 10:00（已过今日9点）→ 次日 09:00，证明非 cron 仍走老算法
    task = SimpleNamespace(
        schedule_type="daily", run_time="09:00", week_day=None,
        interval_minutes=None, last_run_at=None, cron_expr=None,
    )

    nxt = schedule_service._compute_next(task, from_dt=datetime(2026, 7, 15, 10, 0))

    assert nxt == datetime(2026, 7, 16, 9, 0)


def _due_schedule(db, name):
    task = ApifoxSchedule(
        project_id=1, name=name, target_type="case", target_id=1,
        schedule_type="daily", run_time="09:00", enabled=True,
        next_run_at=datetime(2000, 1, 1),  # 已过期 → list_due 选中
    )
    db.add(task)
    db.commit()
    return task


def test_run_due_isolates_failing_task(db, monkeypatch):
    # 两条到期任务，第一条执行抛异常，断言第二条仍被执行且整体不抛
    _due_schedule(db, "bad")
    _due_schedule(db, "good")
    executed = []

    def fake_execute(_db, task):
        if task.name == "bad":
            raise RuntimeError("boom")
        executed.append(task.name)

    monkeypatch.setattr(schedule_service, "execute_schedule", fake_execute)

    schedule_service.run_due_apifox_tasks(db)  # 不应向外抛异常

    assert executed == ["good"]

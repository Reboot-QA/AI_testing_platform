"""工作台活动聚合：定时任务（启用+有下次执行，按 next_run_at 升序）与手工测试单（最近在前）。"""

from datetime import datetime, timedelta

from app.models.apifox.run import ApifoxRun
from app.models.apifox.schedule import ApifoxSchedule
from app.models.test_execution import ManualTestRun
from app.repositories.apifox import workbench_repo as repo


def _run(db, project_id, status, target_type="scenario"):
    r = ApifoxRun(
        project_id=project_id, target_type=target_type, target_id=1, target_name="x", status=status
    )
    db.add(r)
    db.flush()
    return r


def test_recent_runs_filtered_by_status_and_type(db):
    _run(db, 1, "passed", "scenario")
    _run(db, 1, "failed", "scenario")
    _run(db, 1, "failed", "case")
    _run(db, 2, "failed", "scenario")  # 其它项目
    db.commit()

    assert repo.count_runs(db, [1]) == 3
    assert repo.count_runs(db, [1], status="failed") == 2
    assert repo.count_runs(db, [1], status="failed", target_type="scenario") == 1
    assert repo.count_runs(db, [1], target_type="case") == 1
    runs = repo.recent_runs_page(db, [1], 1, 20, status="failed", target_type="scenario")
    assert len(runs) == 1
    assert runs[0].status == "failed" and runs[0].target_type == "scenario"


def _sched(db, project_id, name, enabled=True, next_run_at=None):
    s = ApifoxSchedule(
        project_id=project_id,
        name=name,
        target_type="scenario",
        target_id=1,
        enabled=enabled,
        next_run_at=next_run_at,
    )
    db.add(s)
    db.flush()
    return s


def _manual(db, project_id, name):
    m = ManualTestRun(project_id=project_id, name=name)
    db.add(m)
    db.flush()
    return m


def test_schedules_only_enabled_with_next_run_ordered_asc(db):
    base = datetime(2026, 1, 1, 9, 0, 0)
    _sched(db, 1, "晚", next_run_at=base + timedelta(hours=2))
    _sched(db, 1, "早", next_run_at=base)
    _sched(db, 1, "无时间", next_run_at=None)  # 排除
    _sched(db, 1, "停用", enabled=False, next_run_at=base)  # 排除
    _sched(db, 2, "他项目", next_run_at=base)  # 隔离
    db.commit()

    assert repo.count_schedules(db, [1]) == 2
    items = repo.list_schedules_page(db, [1], 1, 20)
    assert [s.name for s in items] == ["早", "晚"]


def test_manual_runs_scoped_and_recent_first(db):
    _manual(db, 1, "第一轮")
    _manual(db, 1, "第二轮")
    _manual(db, 2, "他项目")
    db.commit()

    assert repo.count_manual_runs(db, [1]) == 2
    items = repo.list_manual_runs_page(db, [1], 1, 20)
    assert [m.name for m in items] == ["第二轮", "第一轮"]


def test_ai_tasks_merged_by_updated_at(db):
    from app.models.apifox.ai_gen_task import ApifoxAiGenTask
    from app.models.hub_ai_task import HubAiTask

    base = datetime(2026, 1, 1, 10, 0, 0)
    h = HubAiTask(
        project_id=1,
        task_type="requirement",
        status="succeeded",
        target="PRD-A",
        updated_at=base,
    )
    a = ApifoxAiGenTask(
        project_id=1,
        status="running",
        categories="[]",
        total_items=2,
        updated_at=base + timedelta(hours=1),
    )
    db.add_all([h, a])
    db.commit()

    assert repo.count_hub_ai_tasks(db, [1]) == 1
    assert repo.count_apifox_ai_gen_tasks(db, [1]) == 1
    hub = repo.list_hub_ai_tasks_recent(db, [1], 5)
    apifox = repo.list_apifox_ai_gen_tasks_recent(db, [1], 5)
    assert len(hub) == 1 and hub[0].target == "PRD-A"
    assert len(apifox) == 1 and apifox[0].status == "running"

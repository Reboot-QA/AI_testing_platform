"""Apifox 运行启动回收（回归：进程被杀后 run 永久卡 running）。"""

from datetime import datetime

from app.models.apifox.run import ApifoxRun, ApifoxRunStep
from app.services.apifox import run_service


def _run(db, status="running", **kw):
    r = ApifoxRun(project_id=1, target_type="scenario", target_id=1, status=status, total_count=1, **kw)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def test_recover_marks_running_run_and_steps_failed(db):
    r = _run(db, status="running", passed_count=0, failed_count=1)
    step = ApifoxRunStep(run_id=r.id, status="running")
    db.add(step)
    db.commit()

    run_service.recover_orphan_runs(db)

    db.refresh(r)
    db.refresh(step)
    assert r.status == "failed"
    assert r.finished_at is not None
    assert step.status == "failed"  # 非终态步骤一并置失败


def test_recover_leaves_terminal_runs_untouched(db):
    passed = _run(db, status="passed", finished_at=datetime(2026, 1, 1))
    failed = _run(db, status="failed")

    run_service.recover_orphan_runs(db)

    db.refresh(passed)
    db.refresh(failed)
    assert passed.status == "passed"
    assert passed.finished_at == datetime(2026, 1, 1)  # 未被改写
    assert failed.status == "failed"

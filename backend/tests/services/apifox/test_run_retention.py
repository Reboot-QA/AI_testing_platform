"""用例级运行报告 30 天保留策略。"""

from datetime import datetime, timedelta

from app.models.apifox.run import ApifoxRun, ApifoxRunStep
from app.repositories.apifox import run_repo
from app.services.apifox import run_retention_service


def test_purge_expired_case_runs_removes_only_old_case_rows(db):
    old = ApifoxRun(
        project_id=1,
        target_type="case",
        target_id=1,
        target_name="旧用例",
        status="passed",
        started_at=datetime.utcnow() - timedelta(days=31),
    )
    recent = ApifoxRun(
        project_id=1,
        target_type="case",
        target_id=2,
        target_name="新用例",
        status="passed",
        started_at=datetime.utcnow() - timedelta(days=1),
    )
    old_scenario = ApifoxRun(
        project_id=1,
        target_type="scenario",
        target_id=3,
        target_name="旧场景",
        status="passed",
        started_at=datetime.utcnow() - timedelta(days=40),
    )
    db.add_all([old, recent, old_scenario])
    db.flush()
    db.add(ApifoxRunStep(run_id=old.id, status="passed", case_name="步骤"))
    db.commit()
    old_id, recent_id, scenario_id = old.id, recent.id, old_scenario.id  # 清理后 old 实例失效，先存 id

    removed = run_retention_service.purge_expired_case_runs(db)

    assert removed == 1
    assert run_repo.get_run(db, old_id) is None
    assert run_repo.get_run(db, recent_id) is not None
    assert run_repo.get_run(db, scenario_id) is not None

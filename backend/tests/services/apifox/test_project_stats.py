"""单项目仪表板统计：counts + 今日通过率 + 近 7 天趋势（补零）。

被测：workbench_service.get_project_stats / workbench_repo.count_suites / daily_trend。
"""

from datetime import datetime, timedelta

from app.models.apifox.run import ApifoxRun
from app.models.apifox.scenario import ApifoxScenario
from app.models.apifox.suite import ApifoxSuite
from app.services.apifox import workbench_service as svc


def _run(db, project_id, status, passed, total, started_at):
    r = ApifoxRun(
        project_id=project_id,
        target_type="case",
        target_id=1,
        target_name="x",
        status=status,
        passed_count=passed,
        total_count=total,
        started_at=started_at,
    )
    db.add(r)
    db.flush()
    return r


def test_project_stats_counts_and_trend(db, make_case):
    make_case(project_id=1, name="c1")  # 建 1 用例（含其接口）
    make_case(project_id=1, name="c2")
    db.add(ApifoxScenario(project_id=1, name="scn"))
    db.add(ApifoxSuite(project_id=1, name="suite"))
    now = datetime.utcnow()
    _run(db, 1, "passed", 8, 10, now)  # 今天：8/10
    _run(db, 1, "failed", 1, 5, now - timedelta(days=2))  # 2 天前：1/5
    _run(db, 2, "passed", 9, 9, now)  # 别项目，不计入
    db.commit()

    stats = svc.get_project_stats(db, 1)

    assert stats["case_count"] == 2
    assert stats["scenario_count"] == 1
    assert stats["suite_count"] == 1
    assert stats["endpoint_count"] == 2  # 每个用例各建一个接口
    assert stats["today_pass_rate"] == 80.0
    assert len(stats["trend"]) == 7  # 近 7 天含今天，补零
    today = stats["trend"][-1]
    assert today["date"] == now.date().isoformat()
    assert (today["passed"], today["total"], today["pass_rate"]) == (8, 10, 80.0)
    two_days_ago = stats["trend"][-3]
    assert (two_days_ago["passed"], two_days_ago["failed"], two_days_ago["total"]) == (1, 4, 5)


def test_project_stats_empty_trend_all_zero(db):
    stats = svc.get_project_stats(db, 999)

    assert stats["case_count"] == 0
    assert stats["today_pass_rate"] is None
    assert len(stats["trend"]) == 7
    assert all(d["total"] == 0 and d["pass_rate"] is None for d in stats["trend"])

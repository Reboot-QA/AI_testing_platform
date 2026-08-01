"""单项目仪表板统计：counts + 今日通过率 + 近 7 天趋势（补零）。

被测：workbench_service.get_project_stats / workbench_repo.count_suites / daily_trend。
"""

from datetime import datetime, timedelta

from app.models.apifox.run import ApifoxRun
from app.models.apifox.scenario import ApifoxScenario
from app.models.apifox.suite import ApifoxSuite
from app.services.apifox import workbench_service as svc


def _run(db, project_id, status, passed, failed, started_at, total=None):
    """建一条已结束 run；total 不传时按引擎常规情形取实际执行数（passed + failed）。"""
    r = ApifoxRun(
        project_id=project_id,
        target_type="case",
        target_id=1,
        target_name="x",
        status=status,
        passed_count=passed,
        failed_count=failed,
        total_count=passed + failed if total is None else total,
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
    _run(db, 1, "passed", 8, 2, now)  # 今天：8 通过 2 失败 = 8/10
    _run(db, 1, "failed", 1, 4, now - timedelta(days=2))  # 2 天前：1/5
    _run(db, 2, "passed", 9, 0, now)  # 别项目，不计入
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


def test_project_stats_pass_rate_not_over_100_when_loops_exceed_planned_total(db):
    """循环/重试让实际执行数超过建 run 时的计划 total_count，通过率不能算出 >100%（否则趋势图被 y 轴截断）。"""
    now = datetime.utcnow()
    _run(db, 1, "passed", 124, 30, now, total=89)  # 计划 89 条，实际跑了 154 条
    db.commit()

    stats = svc.get_project_stats(db, 1)

    today = stats["trend"][-1]
    assert (today["passed"], today["failed"], today["total"]) == (124, 30, 154)
    assert today["pass_rate"] == 80.5
    assert stats["today_pass_rate"] == 80.5


def test_project_stats_empty_trend_all_zero(db):
    stats = svc.get_project_stats(db, 999)

    assert stats["case_count"] == 0
    assert stats["today_pass_rate"] is None
    assert len(stats["trend"]) == 7
    assert all(d["total"] == 0 and d["pass_rate"] is None for d in stats["trend"])

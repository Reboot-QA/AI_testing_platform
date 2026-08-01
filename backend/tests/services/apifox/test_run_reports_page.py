"""项目测试报告分页与失败原因查询。"""

from datetime import date, datetime

from app.models.apifox.run import ApifoxRun, ApifoxRunStep
from app.repositories.apifox import run_repo


def _run(
    db, project_id: int, status: str = "passed", parent_run_id: int | None = None
) -> ApifoxRun:
    run = ApifoxRun(
        project_id=project_id,
        parent_run_id=parent_run_id,
        target_type="scenario",
        target_id=1,
        target_name="场景",
        status=status,
    )
    db.add(run)
    db.flush()
    return run


def _failed_step(db, run_id: int, message: str) -> None:
    db.add(
        ApifoxRunStep(
            run_id=run_id,
            status="failed",
            case_name="失败步骤",
            error_message=message,
        )
    )
    db.flush()


def test_list_runs_page_only_returns_top_level_project_runs(db):
    first = _run(db, 1)
    second = _run(db, 1, "failed")
    _run(db, 1, parent_run_id=second.id)
    _run(db, 2)
    third = _run(db, 1)
    db.commit()

    assert run_repo.count_runs(db, 1) == 3
    assert [run.id for run in run_repo.list_runs_page(db, 1, 1, 2)] == [
        third.id,
        second.id,
    ]
    assert [run.id for run in run_repo.list_runs_page(db, 1, 2, 2)] == [first.id]


def test_failure_reasons_uses_first_direct_failed_step(db):
    run = _run(db, 1, "failed")
    _failed_step(db, run.id, "第一个失败原因")
    _failed_step(db, run.id, "第二个失败原因")
    db.commit()

    assert run_repo.failure_reasons(db, [run.id]) == {run.id: "第一个失败原因"}


def test_failure_reasons_falls_back_to_suite_child(db):
    parent = _run(db, 1, "failed")
    child = _run(db, 1, "failed", parent_run_id=parent.id)
    _failed_step(db, child.id, "套件子运行断言失败")
    db.commit()

    assert run_repo.failure_reasons(db, [parent.id]) == {
        parent.id: "套件子运行断言失败"
    }


def test_list_runs_page_filters_by_target_types(db):
    scenario = _run(db, 1)
    suite = ApifoxRun(
        project_id=1,
        target_type="suite",
        target_id=2,
        target_name="套件",
        status="passed",
    )
    case = ApifoxRun(
        project_id=1,
        target_type="case",
        target_id=3,
        target_name="用例",
        status="passed",
    )
    db.add_all([suite, case])
    db.commit()

    types = ["scenario", "suite"]
    assert run_repo.count_runs(db, 1, types) == 2
    assert {run.target_type for run in run_repo.list_runs_page(db, 1, 1, 10, types)} == {
        "scenario",
        "suite",
    }
    assert scenario.id in {run.id for run in run_repo.list_runs_page(db, 1, 1, 10, types)}


def test_list_runs_page_filters_by_keyword(db):
    hit = ApifoxRun(
        project_id=1, target_type="case", target_id=1, target_name="登录接口", status="passed"
    )
    miss = ApifoxRun(
        project_id=1, target_type="case", target_id=2, target_name="下单接口", status="passed"
    )
    db.add_all([hit, miss])
    db.commit()

    assert run_repo.count_runs(db, 1, keyword="登录") == 1
    assert [r.id for r in run_repo.list_runs_page(db, 1, 1, 10, keyword="登录")] == [hit.id]
    # 空白关键字视同未传，返回全部
    assert run_repo.count_runs(db, 1, keyword="  ") == 2


def test_list_runs_page_filters_by_status(db):
    _run(db, 1, "passed")
    _run(db, 1, "failed")
    _run(db, 1, "failed")
    db.commit()

    assert run_repo.count_runs(db, 1, status="failed") == 2
    assert {r.status for r in run_repo.list_runs_page(db, 1, 1, 10, status="failed")} == {"failed"}


def test_list_runs_page_filters_by_run_id(db):
    hit = _run(db, 1, "failed")
    _run(db, 1, "passed")
    db.commit()

    assert run_repo.count_runs(db, 1, run_id=hit.id) == 1
    assert [r.id for r in run_repo.list_runs_page(db, 1, 1, 10, run_id=hit.id)] == [hit.id]
    assert run_repo.count_runs(db, 1, run_id=999999) == 0


def test_list_runs_page_filters_by_date_range(db):
    def _at(day: int) -> ApifoxRun:
        run = ApifoxRun(
            project_id=1,
            target_type="case",
            target_id=day,
            target_name="用例",
            status="passed",
        )
        run.started_at = datetime(2026, 7, day, 12, 0, 0)
        db.add(run)
        db.flush()
        return run

    d10, d15, d20 = _at(10), _at(15), _at(20)
    db.commit()

    # 闭区间：date_to 当天全天包含在内
    got = {r.id for r in run_repo.list_runs_page(
        db, 1, 1, 10, date_from=date(2026, 7, 15), date_to=date(2026, 7, 20)
    )}
    assert got == {d15.id, d20.id}
    assert run_repo.count_runs(db, 1, date_from=date(2026, 7, 15), date_to=date(2026, 7, 20)) == 2
    # date_from > date_to → 空集
    assert run_repo.count_runs(db, 1, date_from=date(2026, 7, 20), date_to=date(2026, 7, 15)) == 0
    assert d10.id  # 引用避免未使用告警


def _retry_of(db, head: ApifoxRun, attempt: int, status: str = "failed") -> ApifoxRun:
    run = ApifoxRun(
        project_id=head.project_id,
        target_type=head.target_type,
        target_id=head.target_id,
        target_name=head.target_name,
        status=status,
        retry_of_run_id=head.id,
        attempt=attempt,
    )
    db.add(run)
    db.flush()
    return run


def test_pagination_counts_retry_chain_as_one_row(db):
    head = _run(db, 1, "failed")
    _retry_of(db, head, 2)
    last = _retry_of(db, head, 3, "passed")
    other = _run(db, 1)
    db.commit()

    # 一条链只占一行：总数 2（不是 4 次尝试），每页返回的是各链最后一次尝试
    assert run_repo.count_runs(db, 1) == 2
    assert [r.id for r in run_repo.list_runs_page(db, 1, 1, 20)] == [other.id, last.id]
    # 首页装满 page_size 行，不会因折叠而缩水
    assert [r.id for r in run_repo.list_runs_page(db, 1, 1, 1)] == [other.id]
    assert [r.id for r in run_repo.list_runs_page(db, 1, 2, 1)] == [last.id]


def test_status_filter_matches_final_attempt_of_chain(db):
    head = _run(db, 1, "failed")
    _retry_of(db, head, 2)
    last = _retry_of(db, head, 3, "passed")
    db.commit()

    # 整链最终通过 → 归入「通过」，不再因首次失败而出现在「失败」里
    assert [r.id for r in run_repo.list_runs_page(db, 1, 1, 10, status="passed")] == [last.id]
    assert run_repo.count_runs(db, 1, status="failed") == 0


def test_list_retry_chains_returns_earlier_attempts_only(db):
    head = _run(db, 1, "failed")
    second = _retry_of(db, head, 2)
    last = _retry_of(db, head, 3, "passed")
    plain = _run(db, 1)
    db.commit()

    chains = run_repo.list_retry_chains(db, [head.id, plain.id])
    # 代表行（最后一次尝试）不重复出现在子行里；无重试的链不返回
    assert [r.id for r in chains[head.id]] == [head.id, second.id]
    assert last.id not in {r.id for r in chains[head.id]}
    assert plain.id not in chains


def test_chain_head_id_populated_on_create_and_mark_retry(db):
    # 报告分页排序/折叠依赖 chain_head_id：非重试=自身 id，重试经 mark_retry 归入链头 id
    head = _run(db, 1, "failed")
    retry = _run(db, 1, "failed")
    run_repo.mark_retry(db, retry.id, head.id, 2)
    db.commit()
    db.expire_all()

    assert run_repo.get_run(db, head.id).chain_head_id == head.id
    assert run_repo.get_run(db, retry.id).chain_head_id == head.id


def test_delete_runs_removes_steps_and_child_runs(db):
    parent = _run(db, 1, "failed")
    child = _run(db, 1, "failed", parent_run_id=parent.id)
    _failed_step(db, child.id, "子运行失败")
    db.commit()

    parent_id, child_id = parent.id, child.id  # 删除后 ORM 实例失效，先存 id 再断言

    deleted = run_repo.delete_runs(db, [parent_id])
    db.commit()

    assert deleted == 2
    assert run_repo.get_run(db, parent_id) is None
    assert run_repo.get_run(db, child_id) is None
    assert run_repo.list_steps(db, child_id) == []

"""接口用例列表携带「最近一次运行结果 + 失败原因」（供列表失败原因列展示）。"""

from app.models.apifox.case import ApifoxEndpointCase
from app.models.apifox.endpoint import ApifoxEndpoint
from app.models.apifox.run import ApifoxRun, ApifoxRunStep
from app.services.apifox.case_service import list_cases


def _endpoint(db):
    e = ApifoxEndpoint(project_id=1, name="ep", method="GET", path="/x")
    db.add(e)
    db.flush()
    return e


def _case(db, endpoint_id, name):
    c = ApifoxEndpointCase(project_id=1, endpoint_id=endpoint_id, name=name)
    db.add(c)
    db.flush()
    return c


def _run(db, case_id, status):
    r = ApifoxRun(
        project_id=1, target_type="case", target_id=case_id, target_name="x", status=status
    )
    db.add(r)
    db.flush()
    return r


def test_list_cases_carries_latest_run_result_and_reason(db):
    ep = _endpoint(db)
    c_fail = _case(db, ep.id, "失败用例")
    c_pass = _case(db, ep.id, "通过用例")
    _case(db, ep.id, "未运行用例")

    # 失败用例：先通过，再失败（带原因）→ 取最新那次 = 失败
    _run(db, c_fail.id, "passed")
    r_fail = _run(db, c_fail.id, "failed")
    db.add(
        ApifoxRunStep(
            run_id=r_fail.id, status="failed", case_name="步骤", error_message="断言失败：401"
        )
    )
    _run(db, c_pass.id, "passed")
    db.commit()

    briefs = {b.name: b for b in list_cases(db, ep.id)}
    assert briefs["失败用例"].last_result == "failed"
    assert briefs["失败用例"].last_error == "断言失败：401"
    assert briefs["失败用例"].last_run_at is not None
    assert briefs["通过用例"].last_result == "passed"
    assert briefs["通过用例"].last_error is None
    assert briefs["通过用例"].last_run_at is not None
    assert briefs["未运行用例"].last_result is None
    assert briefs["未运行用例"].last_error is None
    assert briefs["未运行用例"].last_run_at is None

"""Apifox AI 生成任务 · 后台 worker 集成测试（mock 模式，不触网）。

覆盖：_run_due 端到端跑通任务、失败隔离（接口缺失→partial/failed）、启动恢复 reset。
用 monkeypatch 强制 mock，隔离 LLM 设置。
"""

import pytest

from app.repositories.apifox import ai_gen_task_repo as repo
from app.routers.apifox.ai_gen_task_schemas import AiGenTaskCreate
from app.routers.apifox.case_schemas import AiGenCategory
from app.services.apifox import ai_gen_task_service as service
from app.services.apifox import ai_gen_worker as worker

_MOCK_CONFIG = {
    "mock_mode": True, "api_key": "", "api_base": "", "model": "",
    "provider_id": None, "provider_name": None,
}


def _force_mock(monkeypatch):
    monkeypatch.setattr(worker, "get_effective_llm_config", lambda db, pid: _MOCK_CONFIG)


def _task(db, endpoint_ids, count=1):
    return service.create_task(
        db, 1, 1,
        AiGenTaskCreate(
            endpoint_ids=endpoint_ids,
            categories=[AiGenCategory(category="positive", count=count)],
        ),
    )


def test_run_due_processes_task_to_succeeded_in_mock_mode(db, make_endpoint, monkeypatch):
    _force_mock(monkeypatch)
    ep1 = make_endpoint(project_id=1, path="/a")
    ep2 = make_endpoint(project_id=1, path="/b")
    task = _task(db, [ep1.id, ep2.id], count=2)

    worker._run_due(db)

    db.refresh(task)
    assert task.status == "succeeded" and task.mode == "mock" and task.done_items == 2
    items = repo.list_items(db, task.id)
    assert all(i.status == "succeeded" and i.generated_count == 2 for i in items)
    assert all(i.result_cases for i in items)
    assert task.finished_at is not None


def test_run_due_no_pending_is_noop(db, monkeypatch):
    _force_mock(monkeypatch)

    worker._run_due(db)  # 无 pending 任务，不应抛异常


def test_run_due_marks_task_failed_when_all_items_fail(db, make_endpoint, monkeypatch):
    _force_mock(monkeypatch)
    ep = make_endpoint(project_id=1)
    task = _task(db, [ep.id])
    db.delete(ep)  # 生成前接口被删 → item 失败
    db.commit()

    worker._run_due(db)

    db.refresh(task)
    assert task.status == "failed"
    assert repo.list_items(db, task.id)[0].status == "failed"


def test_run_due_partial_when_some_items_fail(db, make_endpoint, monkeypatch):
    _force_mock(monkeypatch)
    ok = make_endpoint(project_id=1, path="/ok")
    gone = make_endpoint(project_id=1, path="/gone")
    task = _task(db, [ok.id, gone.id])
    db.delete(gone)
    db.commit()

    worker._run_due(db)

    db.refresh(task)
    assert task.status == "partial"


def test_generate_with_retry_succeeds_on_second_attempt(db, make_endpoint, monkeypatch):
    from app.routers.apifox.case_schemas import CaseCreate
    from app.routers.apifox.schemas import RequestSpec

    calls = {"n": 0}

    async def flaky(db, ep, cats, cfg):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("LLM 请求超时")
        return [CaseCreate(name="c", category="positive", request_spec=RequestSpec())], "llm"

    monkeypatch.setattr(worker.ai_case_service, "generate_cases", flaky)
    ep = make_endpoint(project_id=1)

    cases, mode = worker._generate_with_retry(db, ep, [], {})

    assert calls["n"] == 2 and cases[0].name == "c"  # 第一次超时，第二次成功


def test_generate_with_retry_raises_after_max_attempts(db, make_endpoint, monkeypatch):
    async def always_fail(db, ep, cats, cfg):
        raise ValueError("boom")

    monkeypatch.setattr(worker.ai_case_service, "generate_cases", always_fail)
    ep = make_endpoint(project_id=1)

    with pytest.raises(ValueError):
        worker._generate_with_retry(db, ep, [], {})


def test_reset_running_to_pending_recovers_stuck_tasks(db, make_endpoint):
    ep = make_endpoint(project_id=1)
    task = _task(db, [ep.id])
    task.status = "running"
    repo.list_items(db, task.id)[0].status = "running"
    db.commit()

    n = repo.reset_running_to_pending(db)
    db.commit()

    db.refresh(task)
    assert n == 1 and task.status == "pending"
    assert repo.list_items(db, task.id)[0].status == "pending"


def test_canceled_task_stays_canceled_after_finalize(db, make_endpoint, monkeypatch):
    _force_mock(monkeypatch)
    ep = make_endpoint(project_id=1)
    task = _task(db, [ep.id])
    task.status = "canceled"  # 运行前已被取消
    db.commit()

    worker._finalize(db, task)

    db.refresh(task)
    assert task.status == "canceled" and task.finished_at is not None

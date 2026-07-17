"""Apifox AI 生成任务 · service 集成测试（sqlite 隔离库）。

覆盖：建任务（有效/无效/跨项目过滤）、序列化往返、取消（含幂等）、勾选入库（全量/按下标）。
"""

import pytest

from app.models.apifox.ai_gen_task import ApifoxAiGenTaskItem
from app.repositories.apifox import ai_gen_task_repo as repo
from app.repositories.apifox import case_repo
from app.routers.apifox.ai_gen_task_schemas import AiGenTaskCreate
from app.routers.apifox.case_schemas import AiGenCategory, CaseCreate
from app.routers.apifox.schemas import RequestSpec
from app.services.apifox import ai_gen_task_service as service


def _create(endpoint_ids, categories=None):
    return AiGenTaskCreate(
        endpoint_ids=endpoint_ids,
        categories=categories or [AiGenCategory(category="positive", count=1)],
    )


# ---------- 建任务 ----------
def test_create_task_makes_pending_task_with_one_item_per_endpoint(db, make_endpoint):
    ep1 = make_endpoint(project_id=1, path="/a")
    ep2 = make_endpoint(project_id=1, path="/b")

    task = service.create_task(db, 1, 7, _create([ep1.id, ep2.id]))

    assert task.status == "pending" and task.total_items == 2 and task.created_by == 7
    assert {i.endpoint_id for i in repo.list_items(db, task.id)} == {ep1.id, ep2.id}


def test_create_task_dedupes_repeated_endpoint_ids(db, make_endpoint):
    ep = make_endpoint(project_id=1)

    task = service.create_task(db, 1, 1, _create([ep.id, ep.id, ep.id]))

    assert task.total_items == 1


def test_create_task_raises_when_no_valid_endpoint(db):
    with pytest.raises(ValueError):
        service.create_task(db, 1, 1, _create([99999]))


def test_create_task_filters_endpoint_from_other_project(db, make_endpoint):
    other = make_endpoint(project_id=2)

    with pytest.raises(ValueError):
        service.create_task(db, 1, 1, _create([other.id]))


# ---------- 序列化 ----------
def test_categories_roundtrip():
    cats = [AiGenCategory(category="positive", count=2), AiGenCategory(category="boundary")]

    loaded = service.load_categories(service.dump_categories(cats))

    assert [(c.category, c.count) for c in loaded] == [("positive", 2), ("boundary", None)]


def test_cases_roundtrip():
    cases = [CaseCreate(name="用例1", category="positive", request_spec=RequestSpec())]

    loaded = service.load_cases(service.dump_cases(cases))

    assert [c.name for c in loaded] == ["用例1"]


def test_load_cases_tolerates_none_and_garbage():
    assert service.load_cases(None) == []
    assert service.load_cases("不是JSON") == []


# ---------- 取消 ----------
def test_cancel_pending_task_marks_task_and_items_canceled(db, make_endpoint):
    ep = make_endpoint(project_id=1)
    task = service.create_task(db, 1, 1, _create([ep.id]))

    service.cancel_task(db, task)

    assert task.status == "canceled"
    assert all(i.status == "canceled" for i in repo.list_items(db, task.id))


def test_cancel_is_idempotent_on_terminal_task(db, make_endpoint):
    ep = make_endpoint(project_id=1)
    task = service.create_task(db, 1, 1, _create([ep.id]))
    service.cancel_task(db, task)

    again = service.cancel_task(db, task)  # 再次取消不报错、保持终态

    assert again.status == "canceled"


# ---------- 勾选入库 ----------
def _succeeded_item(db, make_endpoint, cases):
    ep = make_endpoint(project_id=1)
    task = service.create_task(db, 1, 1, _create([ep.id]))
    item = repo.list_items(db, task.id)[0]
    item.result_cases = service.dump_cases(cases)
    item.generated_count = len(cases)
    item.status = "succeeded"
    db.commit()
    return ep, item


def test_apply_item_creates_all_cases_by_default(db, make_endpoint):
    cases = [
        CaseCreate(name="c1", category="positive", request_spec=RequestSpec()),
        CaseCreate(name="c2", category="negative", request_spec=RequestSpec()),
    ]
    ep, item = _succeeded_item(db, make_endpoint, cases)

    result = service.apply_item(db, item, None)

    assert result.created == 2
    assert {c.name for c in case_repo.list_cases(db, ep.id)} == {"c1", "c2"}
    assert item.applied_count == 2


def test_apply_item_creates_only_selected_indexes(db, make_endpoint):
    cases = [
        CaseCreate(name="c1", category="positive", request_spec=RequestSpec()),
        CaseCreate(name="c2", category="negative", request_spec=RequestSpec()),
    ]
    ep, item = _succeeded_item(db, make_endpoint, cases)

    result = service.apply_item(db, item, [1])

    assert result.created == 1
    assert [c.name for c in case_repo.list_cases(db, ep.id)] == ["c2"]


def test_apply_item_ignores_out_of_range_indexes(db, make_endpoint):
    cases = [CaseCreate(name="c1", category="positive", request_spec=RequestSpec())]
    ep, item = _succeeded_item(db, make_endpoint, cases)

    result = service.apply_item(db, item, [5, 9])

    assert result.created == 0


# ---------- task_out ----------
def test_task_out_includes_endpoint_name(db, make_endpoint):
    ep = make_endpoint(project_id=1, name="用户列表", method="GET")
    task = service.create_task(db, 1, 1, _create([ep.id]))

    out = service.task_out(db, task)

    assert out.items[0].endpoint_name == "用户列表" and out.items[0].endpoint_method == "GET"


def test_list_active_returns_pending_task(db, make_endpoint):
    ep = make_endpoint(project_id=1)
    task = service.create_task(db, 1, 1, _create([ep.id]))

    briefs = service.list_active(db, 1)

    assert [b.id for b in briefs] == [task.id]


def test_list_active_excludes_terminal_task(db, make_endpoint):
    ep = make_endpoint(project_id=1)
    task = service.create_task(db, 1, 1, _create([ep.id]))
    service.cancel_task(db, task)

    assert service.list_active(db, 1) == []


def test_list_tasks_page_paginates(db, make_endpoint):
    ep = make_endpoint(project_id=1)
    for _ in range(3):
        service.create_task(db, 1, 1, _create([ep.id]))

    page1 = service.list_tasks_page(db, 1, page=1, page_size=2)
    page2 = service.list_tasks_page(db, 1, page=2, page_size=2)

    assert page1.total == 3 and len(page1.items) == 2 and page1.page == 1
    assert len(page2.items) == 1  # 倒序、第二页剩 1 条


def test_retry_item_resets_failed_item_and_task(db, make_endpoint):
    ep = make_endpoint(project_id=1)
    task = service.create_task(db, 1, 1, _create([ep.id]))
    item = repo.list_items(db, task.id)[0]
    item.status = "failed"
    item.error = "LLM 超时"
    task.status = "partial"
    task.done_items = 1
    db.commit()

    service.retry_item(db, task, item)

    db.refresh(task)
    db.refresh(item)
    assert item.status == "pending" and item.error is None
    assert task.status == "pending" and task.done_items == 0 and task.finished_at is None


def test_retry_item_rejects_non_failed(db, make_endpoint):
    ep = make_endpoint(project_id=1)
    task = service.create_task(db, 1, 1, _create([ep.id]))
    item = repo.list_items(db, task.id)[0]
    item.status = "succeeded"
    task.status = "succeeded"
    db.commit()

    with pytest.raises(ValueError):
        service.retry_item(db, task, item)


def test_retry_item_rejects_when_task_not_finished(db, make_endpoint):
    ep = make_endpoint(project_id=1)
    task = service.create_task(db, 1, 1, _create([ep.id]))  # status=pending
    item = repo.list_items(db, task.id)[0]
    item.status = "failed"
    db.commit()

    with pytest.raises(ValueError):
        service.retry_item(db, task, item)


def test_purge_project_removes_tasks_and_items(db, make_endpoint):
    from app.services.apifox.project_cleanup import purge_project_apifox

    ep = make_endpoint(project_id=1)
    task_id = service.create_task(db, 1, 1, _create([ep.id])).id

    purge_project_apifox(db, 1)
    db.commit()

    assert repo.get_task(db, task_id) is None
    assert repo.list_items(db, task_id) == []


def test_item_model_defaults(db, make_endpoint):
    ep = make_endpoint(project_id=1)
    task = service.create_task(db, 1, 1, _create([ep.id]))

    item = db.query(ApifoxAiGenTaskItem).filter_by(task_id=task.id).first()

    assert item.generated_count == 0 and item.applied_count == 0 and item.result_cases is None

"""Apifox 定时导入 · 调度执行体：成功/失败落终态、下次运行计算、禁用不排程。"""

from types import SimpleNamespace

from app.models.apifox.import_schedule import ApifoxImportSchedule
from app.services.apifox import import_schedule_service as svc


def _schedule(db, **over):
    fields = dict(
        project_id=1,
        name="每日同步",
        url="https://api.x/openapi.json",
        schedule_type="interval",
        interval_minutes=30,
        enabled=True,
    )
    fields.update(over)
    task = ApifoxImportSchedule(**fields)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def test_execute_success_records_status_and_next_run(db, monkeypatch):
    task = _schedule(db)
    monkeypatch.setattr(svc.import_service, "fetch_source", lambda *a, **k: "{}")
    monkeypatch.setattr(svc.import_converters, "to_openapi3", lambda raw: {"openapi": "3.0.0", "paths": {}})
    monkeypatch.setattr(
        svc.import_sync_service,
        "apply_sync",
        lambda *a, **k: SimpleNamespace(added=2, updated=1, deleted=0, kept_referenced=0),
    )

    svc.execute_schedule(db, task)

    assert task.last_run_status == "success"
    assert "新增 2" in (task.last_run_detail or "")
    assert task.next_run_at is not None  # interval 已排下一次


def test_execute_failure_records_failed(db, monkeypatch):
    task = _schedule(db)

    def boom(*a, **k):
        raise ValueError("拉取导入源失败")

    monkeypatch.setattr(svc.import_service, "fetch_source", boom)
    monkeypatch.setattr(svc, "_notify_import_failure", lambda *a, **k: None)

    svc.execute_schedule(db, task)

    assert task.last_run_status == "failed"
    assert "拉取导入源失败" in (task.last_run_detail or "")


def test_disabled_schedule_has_no_next_run(db):
    task = _schedule(db, enabled=False)

    svc.refresh_schedule(db, task)

    assert task.next_run_at is None

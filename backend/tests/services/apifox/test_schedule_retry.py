"""Apifox 定时任务 · 自动重试（仅定时任务，项目级可配）。

隔离重试编排：monkeypatch 掉单次执行/通知/配置，用假 task+db 只验证循环与终态/通知时机。
"""

import types

from app.services.apifox import schedule_service


class FakeDB:
    def commit(self):
        pass


def _task(**kw):
    base = dict(
        id=1, project_id=1, enabled=False,
        last_run_at=None, last_run_id=None, last_run_status=None, next_run_at=None,
    )
    base.update(kw)
    return types.SimpleNamespace(**base)


def _patch(monkeypatch, retry, run_seq):
    """retry=(次数,间隔0)；run_seq=每次 _run_schedule_once 的返回或要抛的异常。返回 (calls, notified)。"""
    seq = iter(run_seq)
    calls: list = []
    notified: list = []

    def run_once(db, task):
        calls.append(1)
        item = next(seq)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(schedule_service, "_retry_config", lambda db, pid: retry)
    monkeypatch.setattr(schedule_service, "_run_schedule_once", run_once)
    monkeypatch.setattr(schedule_service, "_notify_schedule_failure", lambda db, task: notified.append(1))
    return calls, notified


def test_retry_stops_on_first_success_no_notify(monkeypatch):
    calls, notified = _patch(monkeypatch, (3, 0), [("failed", 10), ("passed", 11)])
    task = _task()

    schedule_service.execute_schedule(FakeDB(), task)

    assert len(calls) == 2  # 第 2 次成功即停，不再重试
    assert task.last_run_status == "passed"
    assert task.last_run_id == 11
    assert notified == []  # 成功不通知


def test_retry_exhausted_notifies_once(monkeypatch):
    calls, notified = _patch(monkeypatch, (2, 0), [("failed", None)] * 3)
    task = _task()

    schedule_service.execute_schedule(FakeDB(), task)

    assert len(calls) == 3  # 1 次首跑 + 2 次重试
    assert task.last_run_status == "failed"
    assert notified == [1]  # 全失败才通知一次


def test_no_retry_single_attempt_notifies(monkeypatch):
    calls, notified = _patch(monkeypatch, (0, 5), [("failed", 5)])
    task = _task()

    schedule_service.execute_schedule(FakeDB(), task)

    assert len(calls) == 1  # 不重试只跑一次
    assert notified == [1]


def test_attempt_exception_counts_as_failed_and_retries(monkeypatch):
    calls, notified = _patch(monkeypatch, (2, 0), [RuntimeError("boom"), ("passed", 9)])
    task = _task()

    schedule_service.execute_schedule(FakeDB(), task)

    assert len(calls) == 2  # 首跑异常算失败，第 2 次成功
    assert task.last_run_status == "passed"
    assert task.last_run_id == 9
    assert notified == []


def test_retry_config_reads_project_and_caps_interval(db):
    from app.routers.apifox.notify_schemas import NotifyConfigUpdate
    from app.services.apifox import notify_service

    notify_service.update_config(db, 7, NotifyConfigUpdate(retry_count=3, retry_interval_sec=60))

    assert schedule_service._retry_config(db, 7) == (3, 60)
    assert schedule_service._retry_config(db, 999) == (0, 5)  # 无配置=不重试

"""定时任务「立即执行」：触发即返回、执行体放后台守护线程，不占请求线程（避免套件/多用例超时）。"""

import types

from app.routers.apifox import schedules as router
from app.services.apifox import schedule_service


def test_run_schedule_now_offloads_to_background_not_sync(monkeypatch):
    task = types.SimpleNamespace(id=9, project_id=1)
    monkeypatch.setattr(router, "_owned_schedule", lambda db, sid, user: task)
    monkeypatch.setattr(router, "_out", lambda db, t: {"id": t.id})
    sync_ran: list = []
    bg: list = []
    monkeypatch.setattr(schedule_service, "execute_schedule", lambda d, t: sync_ran.append(t.id))
    monkeypatch.setattr(schedule_service, "run_now_background", lambda sid: bg.append(sid))

    result = router.run_schedule_now(9, db=object(), user=object())

    assert bg == [9]  # 交给后台执行
    assert sync_ran == []  # 请求线程内未同步跑执行体（不阻塞 → 不超时）
    assert result == {"id": 9}

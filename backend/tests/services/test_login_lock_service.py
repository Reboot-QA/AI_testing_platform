"""登录账号锁定策略。"""

from app.services import login_lock_service as svc


def test_lock_threshold():
    assert svc.LOCK_THRESHOLD == 10

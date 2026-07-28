"""回收站剩余保留天数：向上取整、随删除时间递减、到期不为负（时钟一致，无跨时区偏差）。"""

from datetime import datetime, timedelta

from app.services.apifox import trash_service as svc


def test_fresh_delete_shows_full_retention():
    now = datetime(2026, 7, 25, 12, 0, 0)
    assert svc._remaining_days(now, now) == svc.TRASH_RETENTION_DAYS  # 刚删 → 30


def test_remaining_decrements_by_deleted_age():
    now = datetime(2026, 7, 25, 12, 0, 0)
    # 删除 1 天 / 10 天 / 29 天前，剩余随之递减
    assert svc._remaining_days(now - timedelta(days=1), now) == 29
    assert svc._remaining_days(now - timedelta(days=10), now) == 20
    assert svc._remaining_days(now - timedelta(days=29), now) == 1


def test_partial_day_ceils_up():
    now = datetime(2026, 7, 25, 12, 0, 0)
    # 删除 0.5 天前 → 剩余 29.5 天，向上取整为 30
    assert svc._remaining_days(now - timedelta(hours=12), now) == 30


def test_expired_clamped_to_zero():
    now = datetime(2026, 7, 25, 12, 0, 0)
    assert svc._remaining_days(now - timedelta(days=40), now) == 0  # 超期不为负

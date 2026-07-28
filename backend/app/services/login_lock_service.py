"""登录账号锁定：连续密码错误达阈值后锁定，由管理员解锁。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.user import User

LOCK_THRESHOLD = 10


def is_login_locked(user: User) -> bool:
    return bool(user.login_locked)


def record_login_failure(db: Session, user: User | None) -> None:
    if not user:
        return
    user.login_failed_count = (user.login_failed_count or 0) + 1
    if user.login_failed_count >= LOCK_THRESHOLD:
        user.login_locked = True
    db.commit()


def record_login_success(db: Session, user: User) -> None:
    user.login_failed_count = 0
    db.commit()


def admin_lock_user(user: User) -> None:
    user.login_locked = True


def admin_unlock_user(user: User) -> None:
    user.login_locked = False
    user.login_failed_count = 0

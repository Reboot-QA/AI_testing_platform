"""Apifox · 乐观锁版本自增（DB 级原子 CAS，并发下防 last-write-wins）。

expected_version 提供时用 `UPDATE ... WHERE id=:id AND version=:expected SET version=version+1`
原子占坑：并发下只有一个事务能命中(rowcount=1)，其余 rowcount=0 即冲突——不能用应用层
「读→Python 比较→写」，那在多线程/多连接下两个请求会各自算出相等都写成 N+1（评审踩点）。
不提供 expected_version 时退化为普通自增（老客户端，无并发保护，向后兼容）。
"""

from typing import Optional, cast

from sqlalchemy import CursorResult, select, update
from sqlalchemy.orm import Session

from app.services.apifox.errors import ConflictError


def bump_version(db: Session, model, obj, expected_version: Optional[int]) -> None:
    """在其余字段更新之前调用：CAS 命中则 version+1(DB 内)；不命中则 rollback + ConflictError。

    命中后 expire 对象的 version 属性，避免 ORM 用旧值覆盖。model 需有 id/version 列。
    """
    if expected_version is None:
        obj.version += 1  # 老客户端：仅自增，无并发保护
        return
    result = cast(
        CursorResult,
        db.execute(
            update(model)
            .where(model.id == obj.id, model.version == expected_version)
            .values(version=model.version + 1)
        ),
    )
    if result.rowcount == 0:
        db.rollback()
        current = db.execute(select(model.version).where(model.id == obj.id)).scalar_one_or_none()
        raise ConflictError(current if current is not None else expected_version)
    db.expire(obj, ["version"])

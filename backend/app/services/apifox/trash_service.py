"""Apifox 回收站 · 业务层（聚合软删除的场景/套件/用例/接口，按删除时间倒序）。

还原/彻底删的逐类分派在 router（需先按类取实体做项目鉴权），本层只负责列表聚合与到期清理。
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.apifox import case_repo, endpoint_repo, scenario_repo, suite_repo
from app.routers.apifox.trash_schemas import TrashBatchItemIn, TrashBatchOut, TrashItem, TrashPageOut

# 回收站保留期：软删除超过该天数后由调度线程彻底清理
TRASH_RETENTION_DAYS = 30

_PRIORITY_LABEL = {"high": "高", "medium": "中", "low": "低"}


def _expires_at(deleted_at: datetime) -> datetime:
    return deleted_at + timedelta(days=TRASH_RETENTION_DAYS)


def _remaining_days(deleted_at: datetime, now: Optional[datetime] = None) -> int:
    """剩余保留天数（向上取整，最小 0）。deleted_at 与 now 同为 utcnow 时钟，无跨时区偏差。"""
    now = now or datetime.utcnow()
    seconds = (_expires_at(deleted_at) - now).total_seconds()
    return max(0, math.ceil(seconds / 86400))


def _user_names(db: Session, ids: set[int]) -> Dict[int, str]:
    """回收站操作人：展示登录账号 username（无则回退 full_name）。"""
    if not ids:
        return {}
    rows = db.query(User.id, User.full_name, User.username).filter(User.id.in_(ids)).all()
    return {uid: (username or full or str(uid)) for uid, full, username in rows}


def _collect_trash_items(db: Session, project_id: int) -> List[TrashItem]:
    scenarios = scenario_repo.list_deleted_scenarios(db, project_id)
    suites = suite_repo.list_deleted_suites(db, project_id)
    cases = case_repo.list_deleted_cases(db, project_id)
    endpoints = endpoint_repo.list_deleted_endpoints(db, project_id)

    ids = {e.deleted_by for e in scenarios if e.deleted_by}
    ids |= {e.deleted_by for e in suites if e.deleted_by}
    ids |= {case.deleted_by for case, _ in cases if case.deleted_by}
    ids |= {e.deleted_by for e in endpoints if e.deleted_by}
    names = _user_names(db, ids)

    def op(deleted_by: Optional[int]) -> Optional[str]:
        return names.get(deleted_by) if deleted_by else None

    items: List[TrashItem] = []
    for s in scenarios:
        items.append(
            TrashItem(
                kind="scenario",
                id=s.id,
                name=s.name,
                deleted_at=s.deleted_at,
                expires_at=_expires_at(s.deleted_at),
                remaining_days=_remaining_days(s.deleted_at),
                detail=_PRIORITY_LABEL.get(s.priority, s.priority),
                operator=op(s.deleted_by),
            )
        )
    for su in suites:
        items.append(
            TrashItem(
                kind="suite",
                id=su.id,
                name=su.name,
                deleted_at=su.deleted_at,
                expires_at=_expires_at(su.deleted_at),
                remaining_days=_remaining_days(su.deleted_at),
                detail=su.description or None,  # 展示描述，空则前端显示 —
                operator=op(su.deleted_by),
            )
        )
    for case, endpoint in cases:
        items.append(
            TrashItem(
                kind="case",
                id=case.id,
                name=case.name,
                deleted_at=case.deleted_at,
                expires_at=_expires_at(case.deleted_at),
                remaining_days=_remaining_days(case.deleted_at),
                detail=f"{endpoint.method} {endpoint.name}",
                operator=op(case.deleted_by),
            )
        )
    for ep in endpoints:
        items.append(
            TrashItem(
                kind="endpoint",
                id=ep.id,
                name=ep.name,
                deleted_at=ep.deleted_at,
                expires_at=_expires_at(ep.deleted_at),
                remaining_days=_remaining_days(ep.deleted_at),
                detail=f"{ep.method} {ep.path}",
                operator=op(ep.deleted_by),
            )
        )
    items.sort(key=lambda i: i.deleted_at, reverse=True)
    return items


def list_trash(db: Session, project_id: int) -> List[TrashItem]:
    return _collect_trash_items(db, project_id)


def list_trash_page(
    db: Session,
    project_id: int,
    page: int,
    page_size: int,
    keyword: Optional[str] = None,
    kind: Optional[str] = None,
) -> TrashPageOut:
    items = _collect_trash_items(db, project_id)
    if kind:
        items = [i for i in items if i.kind == kind]
    kw = (keyword or "").strip().lower()
    if kw:
        items = [
            i
            for i in items
            if kw in i.name.lower()
            or (i.detail and kw in i.detail.lower())
            or (i.operator and kw in i.operator.lower())
        ]
    total = len(items)
    start = (page - 1) * page_size
    return TrashPageOut(
        items=items[start : start + page_size],
        total=total,
        page=page,
        page_size=page_size,
    )


def _get_deleted(db: Session, project_id: int, kind: str, item_id: int):
    if kind == "scenario":
        obj = scenario_repo.get_scenario(db, item_id)
    elif kind == "suite":
        obj = suite_repo.get_suite(db, item_id)
    elif kind == "case":
        obj = case_repo.get_case(db, item_id)
    elif kind == "endpoint":
        obj = endpoint_repo.get_endpoint(db, item_id)
    else:
        raise ValueError("未知回收站类型")
    if not obj or obj.project_id != project_id:
        raise LookupError("回收站中无此项")
    if obj.deleted_at is None:
        raise ValueError("资源当前不在回收站，无法还原或彻底删除")
    return obj


def _restore_one(db: Session, obj, kind: str) -> None:
    from app.services.apifox import case_service, endpoint_service, scenario_service, suite_service

    if kind == "scenario":
        scenario_service.restore_scenario(db, obj)
    elif kind == "suite":
        suite_service.restore_suite(db, obj)
    elif kind == "endpoint":
        endpoint_service.restore_endpoint(db, obj)
    else:
        case_service.restore_case(db, obj)


def _purge_one(db: Session, obj, kind: str) -> None:
    from app.services.apifox import case_service, endpoint_service, scenario_service, suite_service

    if kind == "scenario":
        scenario_service.purge_scenario(db, obj)
    elif kind == "suite":
        suite_service.purge_suite(db, obj)
    elif kind == "endpoint":
        endpoint_service.purge_endpoint(db, obj)
    else:
        case_service.purge_case(db, obj)


def _label(kind: str, item_id: int, name: str = "") -> str:
    kind_label = {"scenario": "场景", "suite": "测试套件", "case": "接口用例", "endpoint": "单接口"}.get(
        kind, kind
    )
    return f"{kind_label}「{name or item_id}」" if name else f"{kind_label}#{item_id}"


def batch_restore(db: Session, project_id: int, items: list[TrashBatchItemIn]) -> TrashBatchOut:
    succeeded = 0
    errors: list[str] = []
    for item in items:
        try:
            obj = _get_deleted(db, project_id, item.kind, item.id)
            _restore_one(db, obj, item.kind)
            succeeded += 1
        except LookupError:
            errors.append(f"{_label(item.kind, item.id)}：不在回收站或无权访问")
        except ValueError as exc:
            errors.append(f"{_label(item.kind, item.id)}：{exc}")
        except Exception as exc:
            errors.append(f"{_label(item.kind, item.id)}：{exc}")
    return TrashBatchOut(succeeded=succeeded, failed=len(errors), errors=errors)


def batch_purge(db: Session, project_id: int, items: list[TrashBatchItemIn]) -> TrashBatchOut:
    """彻底删除：接口放最后（会级联清除其下用例，避免先删用例后删接口时重复报错）。"""
    kind_rank = {"scenario": 0, "suite": 1, "case": 2, "endpoint": 3}
    ordered = sorted(items, key=lambda i: (kind_rank.get(i.kind, 9), i.id))
    succeeded = 0
    errors: list[str] = []
    for item in ordered:
        name = ""
        try:
            obj = _get_deleted(db, project_id, item.kind, item.id)
            name = getattr(obj, "name", "")
            _purge_one(db, obj, item.kind)
            succeeded += 1
        except LookupError:
            errors.append(f"{_label(item.kind, item.id)}：不在回收站或已删除")
        except ValueError as exc:
            errors.append(f"{_label(item.kind, item.id, name)}：{exc}")
        except Exception as exc:
            errors.append(f"{_label(item.kind, item.id, name)}：{exc}")
    return TrashBatchOut(succeeded=succeeded, failed=len(errors), errors=errors)


def purge_expired(db: Session) -> int:
    """跨项目彻底清理超过保留期的回收站项（调度线程每日调用一次）。返回清理条数。"""
    # 延迟 import 避免服务层顶层循环依赖
    from app.models.apifox.case import ApifoxEndpointCase
    from app.models.apifox.endpoint import ApifoxEndpoint
    from app.models.apifox.scenario import ApifoxScenario
    from app.models.apifox.suite import ApifoxSuite
    from app.services.apifox import (
        case_service,
        endpoint_service,
        scenario_service,
        suite_service,
    )

    cutoff = datetime.utcnow() - timedelta(days=TRASH_RETENTION_DAYS)
    count = 0
    for scn in _expired(db, ApifoxScenario, cutoff):
        scenario_service.purge_scenario(db, scn)
        count += 1
    for su in _expired(db, ApifoxSuite, cutoff):
        suite_service.purge_suite(db, su)
        count += 1
    for case in _expired(db, ApifoxEndpointCase, cutoff):
        case_service.purge_case(db, case)
        count += 1
    # 接口彻底删会级联清理其下用例，故放最后（其用例即便未单独过期也随接口清除）
    for ep in _expired(db, ApifoxEndpoint, cutoff):
        endpoint_service.purge_endpoint(db, ep)
        count += 1
    return count


def _expired(db: Session, model, cutoff: datetime):
    return (
        db.query(model)
        .filter(model.deleted_at.is_not(None), model.deleted_at < cutoff)
        .all()
    )

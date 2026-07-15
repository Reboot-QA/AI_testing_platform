"""用户项目偏好（置顶 / 自定义排序）业务层。"""

from typing import List

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories import user_project_pref_repo as repo
from app.services.project_access_service import get_accessible_project_ids

_NO_PREF_ORDER = 10**9  # 无偏好项目排到有偏好之后，内部保持传入相对序


def order_cards(db: Session, user_id: int, cards: List[dict]) -> List[dict]:
    """给项目卡片附加 pinned 标记并排序：置顶优先 → sort_order → 无偏好者沉底保持原序。

    原地不修改传入列表的元素引用之外的结构；返回新排序后的列表。
    """
    prefs = repo.map_for_user(db, user_id, [c["id"] for c in cards])
    for card in cards:
        pref = prefs.get(card["id"])
        card["pinned"] = bool(pref.pinned) if pref else False

    def sort_key(indexed):
        idx, card = indexed
        pref = prefs.get(card["id"])
        pinned_rank = 0 if (pref and pref.pinned) else 1
        order = pref.sort_order if pref else _NO_PREF_ORDER
        return (pinned_rank, order, idx)

    return [card for _, card in sorted(enumerate(cards), key=sort_key)]


def save_order(db: Session, user: User, items: List[dict]) -> None:
    """按前端传入的展示顺序保存偏好：sort_order=下标，pinned 取各项标记。

    只保存当前用户有权访问的项目，忽略越权/失效 project_id。统一 commit。
    """
    accessible = set(get_accessible_project_ids(db, user))
    order = 0
    for item in items:
        pid = item["project_id"]
        if pid not in accessible:
            continue
        repo.upsert(db, user.id, pid, bool(item.get("pinned")), order)
        order += 1
    db.commit()

"""需求查询兼容：sort_order 列未迁移完成时避免 SELECT 该列导致 500。"""

from functools import lru_cache
from typing import List

from sqlalchemy import inspect
from sqlalchemy.orm import Query, Session, load_only

from app.database import engine
from app.models.requirement import Requirement


@lru_cache(maxsize=1)
def requirement_has_sort_order_column() -> bool:
    inspector = inspect(engine)
    if "requirements" not in inspector.get_table_names():
        return False
    columns = {column["name"] for column in inspector.get_columns("requirements")}
    return "sort_order" in columns


def clear_requirement_column_cache() -> None:
    requirement_has_sort_order_column.cache_clear()


_REQUIREMENT_LIST_LOAD_ONLY = load_only(
    Requirement.id,
    Requirement.project_id,
    Requirement.title,
    Requirement.description,
    Requirement.req_type,
    Requirement.priority,
    Requirement.status,
    Requirement.source,
    Requirement.created_by_id,
    Requirement.created_at,
    Requirement.updated_at,
)

_AI_LOAD_ONLY = load_only(
    Requirement.id,
    Requirement.title,
    Requirement.description,
    Requirement.status,
    Requirement.project_id,
)


def apply_requirement_list_options(query: Query) -> Query:
    if requirement_has_sort_order_column():
        return query
    return query.options(_REQUIREMENT_LIST_LOAD_ONLY)


def apply_requirement_list_order(query: Query) -> Query:
    if requirement_has_sort_order_column():
        return query.order_by(Requirement.sort_order.asc(), Requirement.id.asc())
    return query.order_by(Requirement.id.asc())


def requirement_sort_order_value(req: Requirement) -> int:
    if requirement_has_sort_order_column():
        return req.sort_order or 0
    return 0


def fetch_requirements_for_ai(
    db: Session,
    *,
    project_id: int,
    requirement_ids: List[int],
) -> List[Requirement]:
    query = db.query(Requirement).filter(
        Requirement.id.in_(requirement_ids),
        Requirement.project_id == project_id,
    )
    if not requirement_has_sort_order_column():
        query = query.options(_AI_LOAD_ONLY)
    return query.all()

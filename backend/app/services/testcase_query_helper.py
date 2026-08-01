"""用例查询兼容：sort_order 列未迁移完成时避免 SELECT 该列导致 500。"""

from functools import lru_cache
from typing import List

from sqlalchemy import inspect
from sqlalchemy.orm import Query, load_only

from app.database import engine
from app.models.testcase import TestCase


@lru_cache(maxsize=1)
def testcase_has_sort_order_column() -> bool:
    inspector = inspect(engine)
    if "testcases" not in inspector.get_table_names():
        return False
    columns = {column["name"] for column in inspector.get_columns("testcases")}
    return "sort_order" in columns


def clear_testcase_column_cache() -> None:
    testcase_has_sort_order_column.cache_clear()


_TESTCASE_LIST_LOAD_ONLY = load_only(
    TestCase.id,
    TestCase.project_id,
    TestCase.requirement_id,
    TestCase.title,
    TestCase.case_type,
    TestCase.priority,
    TestCase.preconditions,
    TestCase.steps,
    TestCase.expected_results,
    TestCase.tags,
    TestCase.source,
    TestCase.review_status,
    TestCase.ai_metadata,
    TestCase.created_by_id,
    TestCase.created_at,
    TestCase.updated_at,
)


def apply_testcase_list_options(query: Query) -> Query:
    if testcase_has_sort_order_column():
        return query
    return query.options(_TESTCASE_LIST_LOAD_ONLY)


def apply_testcase_list_order(query: Query) -> Query:
    if testcase_has_sort_order_column():
        return query.order_by(TestCase.sort_order.asc(), TestCase.id.asc())
    return query.order_by(TestCase.id.asc())


def testcase_sort_order_value(case: TestCase) -> int:
    if testcase_has_sort_order_column():
        return case.sort_order or 0
    return 0


def sort_testcases_for_display(cases: List[TestCase]) -> List[TestCase]:
    """与列表 API 一致：sort_order 升序（1 在上），同序号再按 id 升序。"""
    if testcase_has_sort_order_column():
        return sorted(
            cases,
            key=lambda item: (
                testcase_sort_order_value(item) or item.id,
                item.id,
            ),
        )
    return sorted(cases, key=lambda item: item.id)

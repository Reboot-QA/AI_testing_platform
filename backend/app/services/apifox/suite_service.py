"""Apifox 测试套件 · 业务层（CRUD + 套件项校验 + bulk replace + 展示回显）。

套件项引用用例/场景，校验其存在且属本项目。非法输入抛 ValueError（router 转 400）。
写操作末尾 commit。权限在 router。
"""

from typing import List

from sqlalchemy.orm import Session

from app.models.apifox.suite import ApifoxSuite, ApifoxSuiteItem
from app.repositories.apifox import case_repo, endpoint_repo, scenario_repo
from app.repositories.apifox import suite_repo as repo
from app.routers.apifox.suite_schemas import (
    SuiteBrief,
    SuiteCreate,
    SuiteItemIn,
    SuiteItemOut,
    SuiteOut,
    SuiteUpdate,
)
from app.services.apifox import versioning

VALID_TARGET_TYPES = {"case", "scenario"}


def _validate_item(db: Session, suite: ApifoxSuite, item: SuiteItemIn) -> None:
    if item.target_type not in VALID_TARGET_TYPES:
        raise ValueError("套件项类型非法（case/scenario）")
    if item.target_type == "case":
        case = case_repo.get_case(db, item.target_id)
        if not case or case.project_id != suite.project_id:
            raise ValueError("引用的用例不存在或不属于该项目")
    else:
        scenario = scenario_repo.get_scenario(db, item.target_id)
        if not scenario or scenario.project_id != suite.project_id:
            raise ValueError("引用的场景不存在或不属于该项目")


def _write_items(db: Session, suite: ApifoxSuite, items: List[SuiteItemIn]) -> None:
    for i, item in enumerate(items):
        _validate_item(db, suite, item)
        repo.add(
            db,
            ApifoxSuiteItem(
                suite_id=suite.id,
                target_type=item.target_type,
                target_id=item.target_id,
                enabled=item.enabled,
                sort_order=i,
            ),
        )


def _item_out(db: Session, item: ApifoxSuiteItem) -> SuiteItemOut:
    out = SuiteItemOut(
        target_type=item.target_type,
        target_id=item.target_id,
        enabled=item.enabled,
    )
    if item.target_type == "case":
        case = case_repo.get_case(db, item.target_id)
        if case:
            out.target_name = case.name
            endpoint = endpoint_repo.get_endpoint(db, case.endpoint_id)
            if endpoint:
                out.endpoint_method = endpoint.method
                out.endpoint_path = endpoint.path
    else:
        scenario = scenario_repo.get_scenario(db, item.target_id)
        if scenario:
            out.target_name = scenario.name
    return out


def _out(db: Session, suite: ApifoxSuite) -> SuiteOut:
    return SuiteOut(
        id=suite.id,
        project_id=suite.project_id,
        name=suite.name,
        description=suite.description,
        items=[_item_out(db, it) for it in repo.list_items(db, suite.id)],
        sort_order=suite.sort_order,
        version=suite.version,
        created_at=suite.created_at,
        updated_at=suite.updated_at,
    )


def list_suites(db: Session, project_id: int) -> List[SuiteBrief]:
    return [
        SuiteBrief(
            id=s.id,
            name=s.name,
            description=s.description,
            item_count=repo.count_items(db, s.id),
            sort_order=s.sort_order,
        )
        for s in repo.list_suites(db, project_id)
    ]


def create_suite(db: Session, project_id: int, data: SuiteCreate) -> SuiteOut:
    suite = ApifoxSuite(project_id=project_id, name=data.name, description=data.description)
    repo.add(db, suite)
    _write_items(db, suite, data.items)
    db.commit()
    db.refresh(suite)
    return _out(db, suite)


def get_suite_out(db: Session, suite: ApifoxSuite) -> SuiteOut:
    return _out(db, suite)


def _copy_name(db: Session, project_id: int, base: str) -> str:
    candidate = f"{base} 副本"
    n = 2
    while repo.name_exists(db, project_id, candidate):
        candidate = f"{base} 副本{n}"
        n += 1
    return candidate


def copy_suite(db: Session, suite: ApifoxSuite) -> SuiteOut:
    """复制套件：新建套件行 + 拷贝其全部条目（条目仍引用同一批用例/场景）。"""
    new_suite = ApifoxSuite(
        project_id=suite.project_id,
        name=_copy_name(db, suite.project_id, suite.name),
        description=suite.description,
        sort_order=suite.sort_order,
    )
    repo.add(db, new_suite)
    for item in repo.list_items(db, suite.id):
        repo.add(db, ApifoxSuiteItem(
            suite_id=new_suite.id, target_type=item.target_type, target_id=item.target_id,
            enabled=item.enabled, sort_order=item.sort_order,
        ))
    db.commit()
    db.refresh(new_suite)
    return _out(db, new_suite)


def update_suite(db: Session, suite: ApifoxSuite, data: SuiteUpdate) -> SuiteOut:
    # 原子 CAS 先占坑版本（冲突则 rollback+ConflictError，任何字段改动前）
    versioning.bump_version(db, ApifoxSuite, suite, data.expected_version)
    if data.name is not None:
        suite.name = data.name
    if "description" in data.model_fields_set:
        suite.description = data.description
    if data.sort_order is not None:
        suite.sort_order = data.sort_order
    if data.items is not None:
        repo.delete_items(db, suite.id)
        _write_items(db, suite, data.items)
    db.commit()
    db.refresh(suite)
    return _out(db, suite)


def delete_suite(db: Session, suite: ApifoxSuite) -> None:
    repo.delete_items(db, suite.id)
    repo.delete(db, suite)
    db.commit()

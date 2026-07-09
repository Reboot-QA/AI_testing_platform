"""Apifox 接口用例 · 业务层（JSON 列 dump/load + 断言/提取子表 bulk replace）。

用例是聚合根，断言/提取随它一起编辑（PUT 传全量则先删后插，无并发覆盖问题）。
归属校验在 router（case→endpoint→project）。写操作末尾 commit。
"""

import json
from typing import List

from sqlalchemy.orm import Session

from app.models.apifox.case import (
    ApifoxCaseAssertion,
    ApifoxCaseExtract,
    ApifoxEndpointCase,
)
from app.repositories.apifox import case_repo as repo
from app.routers.apifox.case_schemas import (
    AssertionRow,
    CaseBrief,
    CaseCreate,
    CaseOut,
    CaseUpdate,
    DataDrive,
    ExtractRow,
)
from app.routers.apifox.schemas import KvRow, RequestSpec


def _load_request_spec(text: str | None) -> RequestSpec:
    if not text:
        return RequestSpec()
    try:
        return RequestSpec.model_validate_json(text)
    except ValueError:
        return RequestSpec()


def _load_variables(text: str | None) -> List[KvRow]:
    if not text:
        return []
    try:
        return [KvRow(**x) for x in json.loads(text)]
    except (ValueError, TypeError):
        return []


def _dump_variables(rows: List[KvRow]) -> str:
    return json.dumps([r.model_dump() for r in rows], ensure_ascii=False)


def _load_data_drive(text: str | None) -> DataDrive:
    if not text:
        return DataDrive()
    try:
        return DataDrive.model_validate_json(text)
    except ValueError:
        return DataDrive()


def _write_assertions(db: Session, case_id: int, rows: List[AssertionRow]) -> None:
    for i, a in enumerate(rows):
        repo.add(
            db,
            ApifoxCaseAssertion(
                case_id=case_id, type=a.type, path=a.path, expected=a.expected,
                enabled=a.enabled, sort_order=i,
            ),
        )


def _write_extracts(db: Session, case_id: int, rows: List[ExtractRow]) -> None:
    for i, e in enumerate(rows):
        repo.add(
            db,
            ApifoxCaseExtract(
                case_id=case_id, var_name=e.var_name, source=e.source, path=e.path,
                scope=e.scope, enabled=e.enabled, sort_order=i,
            ),
        )


def _case_out(db: Session, case: ApifoxEndpointCase) -> CaseOut:
    return CaseOut(
        id=case.id,
        project_id=case.project_id,
        endpoint_id=case.endpoint_id,
        name=case.name,
        request_spec=_load_request_spec(case.request_spec),
        variables=_load_variables(case.variables),
        data_drive=_load_data_drive(case.data_drive),
        assertions=[
            AssertionRow(type=a.type, path=a.path, expected=a.expected, enabled=a.enabled)
            for a in repo.list_assertions(db, case.id)
        ],
        extracts=[
            ExtractRow(
                var_name=e.var_name, source=e.source, path=e.path, scope=e.scope, enabled=e.enabled
            )
            for e in repo.list_extracts(db, case.id)
        ],
        sort_order=case.sort_order,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def list_cases(db: Session, endpoint_id: int) -> List[CaseBrief]:
    return [
        CaseBrief(id=c.id, endpoint_id=c.endpoint_id, name=c.name, sort_order=c.sort_order)
        for c in repo.list_cases(db, endpoint_id)
    ]


def create_case(db: Session, project_id: int, endpoint_id: int, data: CaseCreate) -> CaseOut:
    case = ApifoxEndpointCase(
        project_id=project_id,
        endpoint_id=endpoint_id,
        name=data.name,
        request_spec=data.request_spec.model_dump_json(),
        variables=_dump_variables(data.variables),
        data_drive=data.data_drive.model_dump_json(),
    )
    repo.add(db, case)
    _write_assertions(db, case.id, data.assertions)
    _write_extracts(db, case.id, data.extracts)
    db.commit()
    db.refresh(case)
    return _case_out(db, case)


def get_case_out(db: Session, case: ApifoxEndpointCase) -> CaseOut:
    return _case_out(db, case)


def update_case(db: Session, case: ApifoxEndpointCase, data: CaseUpdate) -> CaseOut:
    if data.name is not None:
        case.name = data.name
    if data.request_spec is not None:
        case.request_spec = data.request_spec.model_dump_json()
    if data.variables is not None:
        case.variables = _dump_variables(data.variables)
    if data.data_drive is not None:
        case.data_drive = data.data_drive.model_dump_json()
    if data.sort_order is not None:
        case.sort_order = data.sort_order
    if data.assertions is not None:
        repo.delete_assertions(db, case.id)
        _write_assertions(db, case.id, data.assertions)
    if data.extracts is not None:
        repo.delete_extracts(db, case.id)
        _write_extracts(db, case.id, data.extracts)
    db.commit()
    db.refresh(case)
    return _case_out(db, case)


def delete_case(db: Session, case: ApifoxEndpointCase) -> None:
    repo.delete_children(db, case.id)
    repo.delete(db, case)
    db.commit()

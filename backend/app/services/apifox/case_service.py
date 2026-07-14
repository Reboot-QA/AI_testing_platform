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
from app.models.apifox.script import ApifoxCaseScript
from app.repositories.apifox import case_repo as repo
from app.repositories.apifox import scenario_repo, script_repo
from app.routers.apifox.case_schemas import (
    AssertionRow,
    CaseBrief,
    CaseCreate,
    CaseOut,
    CaseScriptOut,
    CaseScriptRef,
    CaseUpdate,
    DataDrive,
    ExtractRow,
    ProjectCaseBrief,
)
from app.routers.apifox.schemas import KvRow, RequestSpec
from app.services.apifox import versioning


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
                case_id=case_id, type=a.type, path=a.path, operator=a.operator,
                expected=a.expected, enabled=a.enabled, sort_order=i,
            ),
        )


def _write_case_scripts(
    db: Session, case: ApifoxEndpointCase, phase: str, refs: List[CaseScriptRef]
) -> None:
    """写入某 phase 的脚本引用；校验脚本存在且属同一 project（否则 ValueError→400）。"""
    for i, ref in enumerate(refs):
        script = script_repo.get_script(db, ref.script_id)
        if not script or script.project_id != case.project_id:
            raise ValueError("引用的脚本不存在或不属于该项目")
        repo.add(
            db,
            ApifoxCaseScript(
                case_id=case.id, script_id=ref.script_id, phase=phase,
                enabled=ref.enabled, sort_order=i,
            ),
        )


def _load_case_scripts(db: Session, case_id: int) -> tuple[List[CaseScriptOut], List[CaseScriptOut]]:
    pre: List[CaseScriptOut] = []
    post: List[CaseScriptOut] = []
    for link in script_repo.list_case_scripts(db, case_id):
        script = script_repo.get_script(db, link.script_id)
        out = CaseScriptOut(
            script_id=link.script_id,
            enabled=link.enabled,
            script_name=script.name if script else "",
            script_lang=script.lang if script else "",
        )
        (pre if link.phase == "pre" else post).append(out)
    return pre, post


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
    pre_scripts, post_scripts = _load_case_scripts(db, case.id)
    return CaseOut(
        pre_scripts=pre_scripts,
        post_scripts=post_scripts,
        id=case.id,
        project_id=case.project_id,
        endpoint_id=case.endpoint_id,
        name=case.name,
        request_spec=_load_request_spec(case.request_spec),
        variables=_load_variables(case.variables),
        data_drive=_load_data_drive(case.data_drive),
        assertions=[
            AssertionRow(type=a.type, path=a.path, operator=a.operator, expected=a.expected, enabled=a.enabled)
            for a in repo.list_assertions(db, case.id)
        ],
        extracts=[
            ExtractRow(
                var_name=e.var_name, source=e.source, path=e.path, scope=e.scope, enabled=e.enabled
            )
            for e in repo.list_extracts(db, case.id)
        ],
        sort_order=case.sort_order,
        version=case.version,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


def list_project_cases(db: Session, project_id: int) -> List[ProjectCaseBrief]:
    """项目全量用例（带接口信息），场景步骤选择器数据源。"""
    return [
        ProjectCaseBrief(
            id=case.id,
            name=case.name,
            endpoint_id=endpoint.id,
            endpoint_name=endpoint.name,
            endpoint_method=endpoint.method,
        )
        for case, endpoint in repo.list_project_cases(db, project_id)
    ]


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
    _write_case_scripts(db, case, "pre", data.pre_scripts)
    _write_case_scripts(db, case, "post", data.post_scripts)
    db.commit()
    db.refresh(case)
    return _case_out(db, case)


def get_case_out(db: Session, case: ApifoxEndpointCase) -> CaseOut:
    return _case_out(db, case)


def update_case(db: Session, case: ApifoxEndpointCase, data: CaseUpdate) -> CaseOut:
    # 原子 CAS 先占坑版本（冲突则 rollback+ConflictError，任何字段改动前）
    versioning.bump_version(db, ApifoxEndpointCase, case, data.expected_version)
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
    if data.pre_scripts is not None:
        script_repo.delete_case_scripts(db, case.id, "pre")
        _write_case_scripts(db, case, "pre", data.pre_scripts)
    if data.post_scripts is not None:
        script_repo.delete_case_scripts(db, case.id, "post")
        _write_case_scripts(db, case, "post", data.post_scripts)
    db.commit()
    db.refresh(case)
    return _case_out(db, case)


def delete_case(db: Session, case: ApifoxEndpointCase) -> None:
    refs = scenario_repo.count_case_refs(db, case.id)
    if refs:
        raise ValueError(f"用例被 {refs} 处场景步骤引用，请先从场景中移除再删除")
    repo.delete_children(db, case.id)
    script_repo.delete_case_scripts(db, case.id)
    repo.delete(db, case)
    db.commit()

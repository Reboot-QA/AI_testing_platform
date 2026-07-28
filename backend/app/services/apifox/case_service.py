"""Apifox 接口用例 · 业务层（JSON 列 dump/load + 断言/提取子表 bulk replace）。

用例是聚合根，断言/提取随它一起编辑（PUT 传全量则先删后插，无并发覆盖问题）。
归属校验在 router（case→endpoint→project）。写操作末尾 commit。
"""

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.case import (
    ApifoxCaseAssertion,
    ApifoxCaseExtract,
    ApifoxEndpointCase,
)
from app.models.apifox.run import ApifoxRun
from app.models.apifox.script import ApifoxCaseScript
from app.repositories.apifox import case_repo as repo
from app.repositories.apifox import endpoint_repo, scenario_repo, script_repo, suite_repo, workbench_repo
from app.routers.apifox.case_schemas import (
    CASE_CATEGORIES,
    AssertionRow,
    CaseBatchDeleteBlockedItem,
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
from app.routers.apifox.schemas import KvRow, ProcessorRow, RequestSpec
from app.services.apifox import sql_script_service, upload_service, versioning


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


def _load_processors(text: str | None) -> List[ProcessorRow]:
    if not text:
        return []
    try:
        return [ProcessorRow(**x) for x in json.loads(text)]
    except (ValueError, TypeError):
        return []


def _dump_processors(rows: List[ProcessorRow]) -> Optional[str]:
    # 空列表存 None：运行时回退旧固定管线（零回归）
    return json.dumps([r.model_dump() for r in rows], ensure_ascii=False) if rows else None


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
        pre_processors=_load_processors(case.pre_processors),
        post_processors=_load_processors(case.post_processors),
        id=case.id,
        project_id=case.project_id,
        endpoint_id=case.endpoint_id,
        name=case.name,
        category=case.category,
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


def _latest_case_runs(db: Session, case_ids: List[int]) -> dict:
    """每个用例的最近一次运行 → (run_id, status, run_at)。"""
    if not case_ids:
        return {}
    rows = (
        db.query(
            ApifoxRun.target_id,
            ApifoxRun.id,
            ApifoxRun.status,
            ApifoxRun.finished_at,
            ApifoxRun.started_at,
        )
        .filter(ApifoxRun.target_type == "case", ApifoxRun.target_id.in_(case_ids))
        .order_by(ApifoxRun.target_id, ApifoxRun.id.desc())
        .all()
    )
    latest: dict = {}
    for target_id, run_id, status, finished_at, started_at in rows:
        if target_id not in latest:
            run_at = finished_at or started_at
            latest[target_id] = (run_id, status, run_at)
    return latest


def list_cases(db: Session, endpoint_id: int) -> List[CaseBrief]:
    cases = repo.list_cases(db, endpoint_id)
    latest = _latest_case_runs(db, [c.id for c in cases])
    reasons = workbench_repo.failure_reasons(
        db, [run_id for run_id, status, _run_at in latest.values() if status == "failed"]
    )
    result = []
    for c in cases:
        run = latest.get(c.id)
        status = run[1] if run else None
        error = reasons.get(run[0]) if run and status == "failed" else None
        result.append(
            CaseBrief(
                id=c.id,
                endpoint_id=c.endpoint_id,
                name=c.name,
                category=c.category,
                origin=c.origin,
                sort_order=c.sort_order,
                last_result=status,
                last_error=error,
                last_run_at=run[2] if run else None,
            )
        )
    return result


def _valid_category(category: str) -> str:
    if category not in CASE_CATEGORIES:
        raise ValueError(f"非法用例分类：{category}")
    return category


def _persist_case(
    db: Session, project_id: int, endpoint_id: int, data: CaseCreate, origin: str = "manual"
) -> ApifoxEndpointCase:
    """写入用例及其断言/提取/脚本子表，不提交事务（供单条与批量创建共用）。origin: manual|ai。"""
    sql_script_service.validate_processor_refs(db, project_id, data.pre_processors)
    sql_script_service.validate_processor_refs(db, project_id, data.post_processors)
    case = ApifoxEndpointCase(
        project_id=project_id,
        endpoint_id=endpoint_id,
        name=data.name,
        category=_valid_category(data.category),
        origin="ai" if origin == "ai" else "manual",
        request_spec=data.request_spec.model_dump_json(),
        variables=_dump_variables(data.variables),
        data_drive=data.data_drive.model_dump_json(),
        pre_processors=_dump_processors(data.pre_processors),
        post_processors=_dump_processors(data.post_processors),
    )
    repo.add(db, case)
    _write_assertions(db, case.id, data.assertions)
    _write_extracts(db, case.id, data.extracts)
    _write_case_scripts(db, case, "pre", data.pre_scripts)
    _write_case_scripts(db, case, "post", data.post_scripts)
    return case


def create_case(db: Session, project_id: int, endpoint_id: int, data: CaseCreate) -> CaseOut:
    case = _persist_case(db, project_id, endpoint_id, data)
    endpoint_repo.clear_cases_stale(db, endpoint_id)  # 新增用例视为已处理该接口的变更
    db.commit()
    db.refresh(case)
    return _case_out(db, case)


def create_cases_bulk(
    db: Session, project_id: int, endpoint_id: int, cases: List[CaseCreate], origin: str = "manual"
) -> tuple[int, int, List[str]]:
    """批量创建用例：同名跳过、单次提交（AI 入库提速，避免逐条 commit）。origin: manual|ai。

    返回 (created, skipped, failed_names)。单条构造异常隔离，不影响其余。
    """
    created = 0
    skipped = 0
    failed: List[str] = []
    seen = {c.name for c in repo.list_cases(db, endpoint_id)}  # 已存在同名一次查全
    for data in cases:
        if data.name in seen:
            skipped += 1
            continue
        try:
            # savepoint 隔离单条失败：坏的一条只回滚自身，已写入的保留
            with db.begin_nested():
                _persist_case(db, project_id, endpoint_id, data, origin=origin)
            seen.add(data.name)  # 同批内重名也去重
            created += 1
        except (ValueError, TypeError):
            failed.append(data.name)
    if created:
        endpoint_repo.clear_cases_stale(db, endpoint_id)
    db.commit()
    return created, skipped, failed


def get_case_out(db: Session, case: ApifoxEndpointCase) -> CaseOut:
    return _case_out(db, case)


def _copy_name(db: Session, endpoint_id: int, base: str) -> str:
    candidate = f"{base} 副本"
    n = 2
    while repo.name_exists(db, endpoint_id, candidate):
        candidate = f"{base} 副本{n}"
        n += 1
    return candidate


def copy_case(db: Session, case: ApifoxEndpointCase) -> CaseOut:
    """复制用例：新建用例行 + 拷贝断言/提取/前后置脚本引用（同接口下）。"""
    new_case = ApifoxEndpointCase(
        project_id=case.project_id, endpoint_id=case.endpoint_id,
        name=_copy_name(db, case.endpoint_id, case.name),
        category=case.category, request_spec=case.request_spec,
        variables=case.variables, data_drive=case.data_drive, sort_order=case.sort_order,
    )
    repo.add(db, new_case)
    for a in repo.list_assertions(db, case.id):
        repo.add(db, ApifoxCaseAssertion(
            case_id=new_case.id, type=a.type, path=a.path, operator=a.operator,
            expected=a.expected, enabled=a.enabled, sort_order=a.sort_order,
        ))
    for e in repo.list_extracts(db, case.id):
        repo.add(db, ApifoxCaseExtract(
            case_id=new_case.id, var_name=e.var_name, source=e.source, path=e.path,
            scope=e.scope, enabled=e.enabled, sort_order=e.sort_order,
        ))
    for link in script_repo.list_case_scripts(db, case.id):
        repo.add(db, ApifoxCaseScript(
            case_id=new_case.id, script_id=link.script_id, phase=link.phase,
            enabled=link.enabled, sort_order=link.sort_order,
        ))
    db.commit()
    db.refresh(new_case)
    return _case_out(db, new_case)


def update_case(db: Session, case: ApifoxEndpointCase, data: CaseUpdate) -> CaseOut:
    # 原子 CAS 先占坑版本（冲突则 rollback+ConflictError，任何字段改动前）
    versioning.bump_version(db, ApifoxEndpointCase, case, data.expected_version)
    if data.name is not None:
        case.name = data.name
    if data.category is not None:
        case.category = _valid_category(data.category)
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
    if data.pre_processors is not None:
        sql_script_service.validate_processor_refs(db, case.project_id, data.pre_processors)
        case.pre_processors = _dump_processors(data.pre_processors)
    if data.post_processors is not None:
        sql_script_service.validate_processor_refs(db, case.project_id, data.post_processors)
        case.post_processors = _dump_processors(data.post_processors)
    endpoint_repo.clear_cases_stale(db, case.endpoint_id)  # 编辑保存用例视为已处理该接口变更
    db.commit()
    db.refresh(case)
    if data.request_spec is not None:  # body 可能移除/替换 binary 文件，清孤儿上传
        upload_service.purge_unreferenced_uploads(db, case.project_id)
    return _case_out(db, case)


def delete_case(db: Session, case: ApifoxEndpointCase, deleted_by: Optional[int] = None) -> None:
    """软删除：移入回收站（可还原）。被场景步骤引用的用例禁止删除。"""
    refs = scenario_repo.count_case_refs(db, case.id)
    if refs:
        raise ValueError(f"用例被 {refs} 处场景步骤引用，请先从场景中移除再删除")
    suite_names = [s.name for s in suite_repo.list_suites_referencing_case(db, case.id)]
    if suite_names:
        raise ValueError(f"用例被测试套件引用（{ '、'.join(suite_names) }），请先从套件中移除再删除")
    case.deleted_at = datetime.utcnow()
    case.deleted_by = deleted_by
    db.commit()


def restore_case(db: Session, case: ApifoxEndpointCase) -> None:
    """从回收站还原。"""
    case.deleted_at = None
    db.commit()


def batch_delete_cases(
    db: Session,
    endpoint_id: int,
    case_ids: List[int],
    deleted_by: Optional[int] = None,
    detach_refs: bool = False,
) -> tuple[int, List[str], List[CaseBatchDeleteBlockedItem]]:
    """批量软删除该接口下的用例（移入回收站）。被场景/套件引用的默认跳过并回其名。

    detach_refs=True 时先移除场景步骤与套件项中的引用，再删除用例。
    返回 (deleted, blocked_names, blocked_details)。仅删属于该接口且未删除的用例，越权 id 忽略。
    """
    id_set = {i for i in case_ids}
    deleted = 0
    blocked: List[str] = []
    blocked_details: List[CaseBatchDeleteBlockedItem] = []
    now = datetime.utcnow()
    if detach_refs and id_set:
        scenario_repo.detach_case_refs(db, id_set)
        suite_repo.detach_case_refs(db, id_set)
    for c in repo.list_cases(db, endpoint_id):
        if c.id not in id_set:
            continue
        if not detach_refs:
            scenarios = [s.name for s in scenario_repo.list_scenarios_referencing_case(db, c.id)]
            suites = [s.name for s in suite_repo.list_suites_referencing_case(db, c.id)]
            if scenarios or suites:
                blocked.append(c.name)
                blocked_details.append(
                    CaseBatchDeleteBlockedItem(name=c.name, scenarios=scenarios, suites=suites)
                )
                continue
        c.deleted_at = now
        c.deleted_by = deleted_by
        deleted += 1
    db.commit()
    return deleted, blocked, blocked_details


def purge_case(db: Session, case: ApifoxEndpointCase) -> None:
    """彻底删除：连同断言/提取/脚本物理删除，不可恢复。"""
    repo.delete_children(db, case.id)
    script_repo.delete_case_scripts(db, case.id)
    repo.delete(db, case)
    db.commit()

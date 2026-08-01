"""Apifox · 更新 Swagger（增量同步）。

对比新 OpenAPI 与库中接口，按 (method, path) 分「新增/变更/移除」：
- 变更：只同步请求契约（query/path/header/body），保留本地命名与 cookies/auth/settings；用例不动，仅告知。
- 移除：无引用可删（连同用例），被场景/套件引用的用例不自动删，只给修改提示。
compute_diff 为纯只读预览；apply_sync 才写库、单次 commit。
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.endpoint import ApifoxEndpoint, ApifoxFolder
from app.repositories.apifox import case_repo, scenario_repo, script_repo, suite_repo
from app.repositories.apifox import endpoint_repo as repo
from app.routers.apifox.schemas import (
    ImportCaseRef,
    ImportChangedEndpoint,
    ImportDiffEndpoint,
    ImportDiffOut,
    ImportRemovedEndpoint,
    ImportRunItem,
    ImportSyncReport,
)
from app.services.apifox import import_service

# 逐条清单落库上限，防单次同步大量接口撑爆 last_run_manifest 列
_MAX_MANIFEST_ITEMS = 1000

# 契约装载/比对/覆盖与「导入时覆盖已存在接口」同一套语义，单一实现放在 import_service
_load_spec = import_service.load_spec
_change_labels = import_service.change_labels
_apply_contract = import_service.apply_contract


def _removed_endpoint(db: Session, ep: ApifoxEndpoint) -> ImportRemovedEndpoint:
    """移除项 + 其用例被场景/套件引用的情况（referenced=True 即不自动删）。"""
    cases = case_repo.list_cases(db, ep.id)
    refs: List[ImportCaseRef] = []
    for case in cases:
        scenarios = [s.name for s in scenario_repo.list_scenarios_referencing_case(db, case.id)]
        suites = [s.name for s in suite_repo.list_suites_referencing_case(db, case.id)]
        if scenarios or suites:
            refs.append(
                ImportCaseRef(case_id=case.id, case_name=case.name, scenarios=scenarios, suites=suites)
            )
    return ImportRemovedEndpoint(
        endpoint_id=ep.id,
        method=ep.method,
        path=ep.path,
        name=ep.name,
        case_count=len(cases),
        referenced=bool(refs),
        references=refs,
    )


def compute_diff(db: Session, project_id: int, doc: Dict[str, Any]) -> ImportDiffOut:
    """只读预览：新增/变更/移除 + 新增 schema 数。不写库。"""
    import_service.validate_openapi(doc)
    parsed = import_service.parse_openapi(doc)
    parsed_by_key = {(it["method"], it["path"]): it for it in parsed}
    existing_by_key = {(e.method.upper(), e.path): e for e in repo.list_endpoints(db, project_id)}

    added: List[ImportDiffEndpoint] = []
    changed: List[ImportChangedEndpoint] = []
    for key, item in parsed_by_key.items():
        ep = existing_by_key.get(key)
        if ep is None:
            added.append(ImportDiffEndpoint(method=item["method"], path=item["path"], name=item["name"]))
            continue
        labels = _change_labels(item["request_spec"], _load_spec(ep.request_spec))
        if labels:
            cases = case_repo.list_cases(db, ep.id)
            changed.append(
                ImportChangedEndpoint(
                    endpoint_id=ep.id,
                    method=ep.method,
                    path=ep.path,
                    name=ep.name,
                    changes=labels,
                    affected_cases=[c.name for c in cases],
                )
            )

    removed = [
        _removed_endpoint(db, ep)
        for key, ep in existing_by_key.items()
        if key not in parsed_by_key
    ]
    return ImportDiffOut(
        added=added,
        changed=changed,
        removed=removed,
        schemas_added=import_service.count_new_schemas(db, project_id, doc),
    )


def _delete_endpoint_cascade(db: Session, ep: ApifoxEndpoint) -> None:
    """删接口 + 其全部用例（含回收站已软删，用例已确认无引用）+ 两级处理器子表。"""
    for case in case_repo.list_cases_all(db, ep.id):
        case_repo.delete_children(db, case.id)
        script_repo.delete_case_scripts(db, case.id)
        case_repo.delete(db, case)
    repo.delete_endpoint_assertions(db, ep.id)
    repo.delete_endpoint_extracts(db, ep.id)
    script_repo.delete_endpoint_scripts(db, ep.id)
    repo.delete_endpoint(db, ep)


def _reference_warning(ep: ApifoxEndpoint, ref: ImportCaseRef) -> str:
    where = "、".join(
        [f"场景「{s}」" for s in ref.scenarios] + [f"套件「{s}」" for s in ref.suites]
    )
    return (
        f"接口「{ep.name}」({ep.method} {ep.path}) 已在新 Swagger 移除，"
        f"但其用例「{ref.case_name}」仍被 {where} 引用，请先处理引用后再手动删除。"
    )


def apply_sync(
    db: Session, project_id: int, doc: Dict[str, Any], delete_unreferenced: bool
) -> ImportSyncReport:
    """应用同步：建新增、更新变更契约、按需删无引用移除项；有引用只告警。单次 commit。"""
    import_service.validate_openapi(doc)
    parsed = import_service.parse_openapi(doc)
    parsed_by_key = {(it["method"], it["path"]): it for it in parsed}
    existing_by_key = {(e.method.upper(), e.path): e for e in repo.list_endpoints(db, project_id)}
    folder_by_name: Dict[str, ApifoxFolder] = {
        f.name: f for f in repo.list_folders(db, project_id) if f.parent_id is None
    }

    report = ImportSyncReport()
    manifest: List[ImportRunItem] = []

    def _add(method: str, path: str, folder: Optional[str], name: str, status: str) -> None:
        if len(manifest) < _MAX_MANIFEST_ITEMS:
            manifest.append(
                ImportRunItem(method=method, path=path, folder=folder or "", name=name, status=status)
            )
        else:
            report.truncated = True

    for key, item in parsed_by_key.items():
        ep = existing_by_key.get(key)
        if ep is None:
            import_service.create_endpoint_from_item(db, project_id, item, folder_by_name)
            report.added += 1
            _add(item["method"], item["path"], item.get("folder"), item.get("name") or "", "added")
            continue
        old_spec = _load_spec(ep.request_spec)
        if _change_labels(item["request_spec"], old_spec):
            _apply_contract(ep, item["request_spec"], old_spec)
            if case_repo.list_cases(db, ep.id):
                ep.cases_stale = True  # 有用例则标记待复核，供树上提示
            report.updated += 1
            _add(item["method"], item["path"], item.get("folder"), item.get("name") or "", "updated")
        else:
            report.skipped += 1
            _add(item["method"], item["path"], item.get("folder"), item.get("name") or "", "skipped")

    for key, ep in existing_by_key.items():
        if key in parsed_by_key:
            continue
        removed = _removed_endpoint(db, ep)
        if removed.referenced:
            report.kept_referenced += 1
            report.warnings.extend(_reference_warning(ep, ref) for ref in removed.references)
            _add(ep.method, ep.path, None, ep.name or "", "kept")
        elif delete_unreferenced:
            _delete_endpoint_cascade(db, ep)
            report.deleted += 1
            _add(ep.method, ep.path, None, ep.name or "", "deleted")

    report.items = manifest
    report.schemas_created = import_service.import_schemas(db, project_id, doc)
    db.commit()
    return report

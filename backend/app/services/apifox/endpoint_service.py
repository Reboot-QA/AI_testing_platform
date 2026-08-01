"""Apifox 接口管理 · 业务层（校验归属 + 编排 repository + request_spec JSON 序列化）。

归属：folder/endpoint 必须属于已通过 project_access 校验的 project；跨项目引用抛 ValueError（router 转 400）。
不做权限判定（在 router 用 project_access_service）。提交事务由本层负责（写操作末尾 commit）。
"""

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.apifox.endpoint import (
    ApifoxEndpoint,
    ApifoxEndpointAssertion,
    ApifoxEndpointExtract,
    ApifoxFolder,
)
from app.models.apifox.script import ApifoxEndpointScript
from app.models.project import Project
from app.repositories.apifox import case_repo, scenario_repo, schema_repo, script_repo
from app.repositories.apifox import endpoint_repo as repo
from app.routers.apifox.schemas import (
    AssertionRow,
    CaseScriptOut,
    CaseScriptRef,
    EndpointBrief,
    EndpointCreate,
    EndpointOut,
    EndpointUpdate,
    ExtractRow,
    FolderCreate,
    FolderOut,
    FolderUpdate,
    ProcessorRow,
    RequestSpec,
    TreeReorderRequest,
)
from app.services.apifox import sql_script_service, upload_service, versioning


class OrderVersionConflictError(Exception):
    """排序快照已过期，需要客户端刷新后重试。"""


def _load_spec(text: str | None) -> RequestSpec:
    if not text:
        return RequestSpec()
    try:
        return RequestSpec.model_validate_json(text)
    except ValueError:
        return RequestSpec()


def _folder_out(folder: ApifoxFolder) -> FolderOut:
    return FolderOut(
        id=folder.id,
        project_id=folder.project_id,
        parent_id=folder.parent_id,
        name=folder.name,
        sort_order=folder.sort_order,
    )


# ---------- 接口级处理器（断言/提取/前后置脚本，镜像 case_service） ----------
def _write_endpoint_assertions(db: Session, endpoint_id: int, rows: List[AssertionRow]) -> None:
    for i, a in enumerate(rows):
        repo.add(
            db,
            ApifoxEndpointAssertion(
                endpoint_id=endpoint_id, type=a.type, path=a.path, operator=a.operator,
                expected=a.expected, enabled=a.enabled, sort_order=i,
            ),
        )


def _write_endpoint_extracts(db: Session, endpoint_id: int, rows: List[ExtractRow]) -> None:
    for i, e in enumerate(rows):
        repo.add(
            db,
            ApifoxEndpointExtract(
                endpoint_id=endpoint_id, var_name=e.var_name, source=e.source, path=e.path,
                scope=e.scope, enabled=e.enabled, sort_order=i,
            ),
        )


def _write_endpoint_scripts(
    db: Session, endpoint: ApifoxEndpoint, phase: str, refs: List[CaseScriptRef]
) -> None:
    for i, ref in enumerate(refs):
        script = script_repo.get_script(db, ref.script_id)
        if not script or script.project_id != endpoint.project_id:
            raise ValueError("引用的脚本不存在或不属于该项目")
        script_repo.add(
            db,
            ApifoxEndpointScript(
                endpoint_id=endpoint.id, script_id=ref.script_id, phase=phase,
                enabled=ref.enabled, sort_order=i,
            ),
        )


def _load_endpoint_scripts(db: Session, endpoint_id: int) -> tuple[List[CaseScriptOut], List[CaseScriptOut]]:
    pre: List[CaseScriptOut] = []
    post: List[CaseScriptOut] = []
    for link in script_repo.list_endpoint_scripts(db, endpoint_id):
        script = script_repo.get_script(db, link.script_id)
        out = CaseScriptOut(
            script_id=link.script_id,
            enabled=link.enabled,
            script_name=script.name if script else "",
            script_lang=script.lang if script else "",
        )
        (pre if link.phase == "pre" else post).append(out)
    return pre, post


def _load_processors(text) -> List[ProcessorRow]:
    if not text:
        return []
    try:
        return [ProcessorRow(**x) for x in json.loads(text)]
    except (ValueError, TypeError):
        return []


def _dump_processors(rows) -> Optional[str]:
    return json.dumps([r.model_dump() for r in rows], ensure_ascii=False) if rows else None


def _endpoint_out(db: Session, endpoint: ApifoxEndpoint) -> EndpointOut:
    pre_scripts, post_scripts = _load_endpoint_scripts(db, endpoint.id)
    return EndpointOut(
        id=endpoint.id,
        project_id=endpoint.project_id,
        folder_id=endpoint.folder_id,
        name=endpoint.name,
        method=endpoint.method,
        path=endpoint.path,
        server_name=endpoint.server_name,
        request_spec=_load_spec(endpoint.request_spec),
        description=endpoint.description,
        sort_order=endpoint.sort_order,
        version=endpoint.version,
        response_schema_id=endpoint.response_schema_id,
        contract_strict=endpoint.contract_strict,
        assertions=[
            AssertionRow(type=a.type, path=a.path, operator=a.operator, expected=a.expected, enabled=a.enabled)
            for a in repo.list_endpoint_assertions(db, endpoint.id)
        ],
        extracts=[
            ExtractRow(var_name=e.var_name, source=e.source, path=e.path, scope=e.scope, enabled=e.enabled)
            for e in repo.list_endpoint_extracts(db, endpoint.id)
        ],
        pre_scripts=pre_scripts,
        post_scripts=post_scripts,
        pre_processors=_load_processors(endpoint.pre_processors),
        post_processors=_load_processors(endpoint.post_processors),
        created_at=endpoint.created_at,
        updated_at=endpoint.updated_at,
    )


def _require_folder_in_project(db: Session, folder_id: int | None, project_id: int) -> None:
    if folder_id is None:
        return
    folder = repo.get_folder(db, folder_id)
    if not folder or folder.project_id != project_id:
        raise ValueError("所选文件夹不存在或不属于该项目")


def _require_schema_in_project(db: Session, schema_id: int | None, project_id: int) -> None:
    if schema_id is None:
        return
    schema = schema_repo.get_schema(db, schema_id)
    if not schema or schema.project_id != project_id:
        raise ValueError("所选响应模型不存在或不属于该项目")


def _would_create_cycle(db: Session, folder_id: int, new_parent_id: int | None, project_id: int) -> bool:
    """把 folder 移到 new_parent 下是否形成环（new_parent 是 folder 自身或其子孙）。"""
    if new_parent_id is None:
        return False
    if new_parent_id == folder_id:
        return True
    folders_by_id = {f.id: f for f in repo.list_folders(db, project_id)}
    cur_id: int | None = new_parent_id
    seen: set[int] = set()
    while cur_id is not None:
        if cur_id == folder_id:
            return True
        if cur_id in seen:
            break
        seen.add(cur_id)
        parent = folders_by_id.get(cur_id)
        cur_id = parent.parent_id if parent else None
    return False


def _has_cycle(folders_by_id: dict[int, ApifoxFolder]) -> bool:
    """整棵文件夹图是否存在环（按当前 parent_id 关系走链）。"""
    for folder in folders_by_id.values():
        cur_id: int | None = folder.id
        seen: set[int] = set()
        while cur_id is not None:
            if cur_id in seen:
                return True
            seen.add(cur_id)
            node = folders_by_id.get(cur_id)
            cur_id = node.parent_id if node else None
    return False


# ---------- folders ----------
def list_folders(db: Session, project_id: int) -> List[FolderOut]:
    return [_folder_out(f) for f in repo.list_folders(db, project_id)]


def create_folder(db: Session, project_id: int, data: FolderCreate) -> FolderOut:
    _require_folder_in_project(db, data.parent_id, project_id)
    folder = ApifoxFolder(
        project_id=project_id,
        parent_id=data.parent_id,
        name=data.name,
        sort_order=repo.next_folder_sort_order(db, project_id, data.parent_id),
    )
    repo.create_folder(db, folder)
    db.commit()
    db.refresh(folder)
    return _folder_out(folder)


def update_folder(db: Session, folder: ApifoxFolder, data: FolderUpdate) -> FolderOut:
    if "parent_id" in data.model_fields_set:
        _require_folder_in_project(db, data.parent_id, folder.project_id)
        if _would_create_cycle(db, folder.id, data.parent_id, folder.project_id):
            raise ValueError("文件夹不能移动到自身或其子文件夹下")
        folder.parent_id = data.parent_id
    if data.name is not None:
        folder.name = data.name
    if data.sort_order is not None:
        folder.sort_order = data.sort_order
    db.commit()
    db.refresh(folder)
    return _folder_out(folder)


def _assert_endpoint_soft_deletable(db: Session, endpoint: ApifoxEndpoint) -> None:
    for case in case_repo.list_cases(db, endpoint.id):
        refs = scenario_repo.count_case_refs(db, case.id)
        if refs:
            raise ValueError(
                f"接口「{endpoint.name}」的用例「{case.name}」被 {refs} 处场景步骤引用，"
                "请先从场景中移除再删除"
            )


def _soft_delete_endpoint(db: Session, endpoint: ApifoxEndpoint) -> None:
    _assert_endpoint_soft_deletable(db, endpoint)
    endpoint.deleted_at = datetime.utcnow()


def _subtree_folder_ids(folders: List[ApifoxFolder], root_id: int) -> set[int]:
    ids = {f.id for f in folders}
    by_parent: dict[int | None, list[int]] = {}
    for f in folders:
        by_parent.setdefault(f.parent_id, []).append(f.id)
    out: set[int] = set()
    stack = [root_id]
    while stack:
        fid = stack.pop()
        if fid not in ids or fid in out:
            continue
        out.add(fid)
        stack.extend(by_parent.get(fid, []))
    return out


def _folders_deepest_first(folder_ids: set[int], folders_by_id: dict[int, ApifoxFolder]) -> list[int]:
    def depth(fid: int) -> int:
        d = 0
        cur = folders_by_id.get(fid)
        while cur and cur.parent_id is not None and cur.parent_id in folder_ids:
            d += 1
            cur = folders_by_id.get(cur.parent_id)
        return d

    return sorted(folder_ids, key=depth, reverse=True)


def delete_folder(db: Session, folder: ApifoxFolder, deleted_by: Optional[int] = None) -> None:
    """删除文件夹及其全部子文件夹；其下接口软删除进回收站（可还原）。"""
    all_folders = repo.list_folders(db, folder.project_id)
    folders_by_id = {f.id: f for f in all_folders}
    subtree_ids = _subtree_folder_ids(all_folders, folder.id)
    if folder.id not in subtree_ids:
        raise ValueError("文件夹不存在或不属于该项目")

    endpoints_to_delete = [
        ep for ep in repo.list_endpoints(db, folder.project_id) if ep.folder_id in subtree_ids
    ]
    for ep in endpoints_to_delete:
        _assert_endpoint_soft_deletable(db, ep)
    for ep in endpoints_to_delete:
        ep.deleted_at = datetime.utcnow()
        ep.deleted_by = deleted_by
        ep.folder_id = None  # 解除 FK，MySQL 下否则无法删除 apifox_folders 行

    # 回收站里仍挂在该子树下的接口也要解除 FK（否则 MySQL 报 1451 外键违反 → 500）；
    # 只动 folder_id，保留原本的删除时间与操作人，回收站展示不受影响
    for ep in repo.list_deleted_endpoints(db, folder.project_id):
        if ep.folder_id in subtree_ids:
            ep.folder_id = None

    # 先断开子树内 parent_id 自引用：SQLAlchemy 会把多行 DELETE 打成 executemany，
    # 按主键顺序删（父先于子）→ MySQL/SQLite FK 1451；断开后再删则与顺序无关。
    for fid in subtree_ids:
        folders_by_id[fid].parent_id = None
    db.flush()

    for fid in _folders_deepest_first(subtree_ids, folders_by_id):
        repo.delete_folder(db, folders_by_id[fid])
    db.commit()


# ---------- endpoints ----------
def list_endpoints(db: Session, project_id: int) -> List[EndpointBrief]:
    return [
        EndpointBrief(
            id=e.id,
            folder_id=e.folder_id,
            name=e.name,
            method=e.method,
            path=e.path,
            sort_order=e.sort_order,
            cases_stale=e.cases_stale,
        )
        for e in repo.list_endpoints(db, project_id)
    ]


def create_endpoint(db: Session, project_id: int, data: EndpointCreate) -> EndpointOut:
    _require_folder_in_project(db, data.folder_id, project_id)
    _require_schema_in_project(db, data.response_schema_id, project_id)
    sql_script_service.validate_processor_refs(db, project_id, data.pre_processors)
    sql_script_service.validate_processor_refs(db, project_id, data.post_processors)
    endpoint = ApifoxEndpoint(
        project_id=project_id,
        folder_id=data.folder_id,
        name=data.name,
        method=data.method,
        path=data.path,
        server_name=data.server_name,
        sort_order=repo.next_endpoint_sort_order(db, project_id, data.folder_id),
        request_spec=data.request_spec.model_dump_json(),
        description=data.description,
        response_schema_id=data.response_schema_id,
        contract_strict=data.contract_strict,
        pre_processors=_dump_processors(data.pre_processors),
        post_processors=_dump_processors(data.post_processors),
    )
    repo.create_endpoint(db, endpoint)  # flush 后 endpoint.id 可用
    _write_endpoint_assertions(db, endpoint.id, data.assertions)
    _write_endpoint_extracts(db, endpoint.id, data.extracts)
    _write_endpoint_scripts(db, endpoint, "pre", data.pre_scripts)
    _write_endpoint_scripts(db, endpoint, "post", data.post_scripts)
    db.commit()
    db.refresh(endpoint)
    return _endpoint_out(db, endpoint)


def get_endpoint_out(db: Session, endpoint: ApifoxEndpoint) -> EndpointOut:
    return _endpoint_out(db, endpoint)


def update_endpoint(db: Session, endpoint: ApifoxEndpoint, data: EndpointUpdate) -> EndpointOut:
    # 原子 CAS 先占坑版本（冲突则 rollback+ConflictError，任何字段改动前）
    versioning.bump_version(db, ApifoxEndpoint, endpoint, data.expected_version)
    if "folder_id" in data.model_fields_set:
        _require_folder_in_project(db, data.folder_id, endpoint.project_id)
        endpoint.folder_id = data.folder_id
    if data.name is not None:
        endpoint.name = data.name
    if data.method is not None:
        endpoint.method = data.method
    if data.path is not None:
        endpoint.path = data.path
    if "server_name" in data.model_fields_set:
        endpoint.server_name = data.server_name
    if data.request_spec is not None:
        endpoint.request_spec = data.request_spec.model_dump_json()
    if data.description is not None:
        endpoint.description = data.description
    if data.sort_order is not None:
        endpoint.sort_order = data.sort_order
    if "response_schema_id" in data.model_fields_set:
        _require_schema_in_project(db, data.response_schema_id, endpoint.project_id)
        endpoint.response_schema_id = data.response_schema_id
    if data.contract_strict is not None:
        endpoint.contract_strict = data.contract_strict
    # 处理器：提供即整组替换（先删后插）
    if data.assertions is not None:
        repo.delete_endpoint_assertions(db, endpoint.id)
        _write_endpoint_assertions(db, endpoint.id, data.assertions)
    if data.extracts is not None:
        repo.delete_endpoint_extracts(db, endpoint.id)
        _write_endpoint_extracts(db, endpoint.id, data.extracts)
    if data.pre_scripts is not None:
        script_repo.delete_endpoint_scripts(db, endpoint.id, "pre")
        _write_endpoint_scripts(db, endpoint, "pre", data.pre_scripts)
    if data.post_scripts is not None:
        script_repo.delete_endpoint_scripts(db, endpoint.id, "post")
        _write_endpoint_scripts(db, endpoint, "post", data.post_scripts)
    if data.pre_processors is not None:
        sql_script_service.validate_processor_refs(db, endpoint.project_id, data.pre_processors)
        endpoint.pre_processors = _dump_processors(data.pre_processors)
    if data.post_processors is not None:
        sql_script_service.validate_processor_refs(db, endpoint.project_id, data.post_processors)
        endpoint.post_processors = _dump_processors(data.post_processors)
    db.commit()
    db.refresh(endpoint)
    if data.request_spec is not None:  # body 可能移除/替换 binary 文件，清孤儿上传
        upload_service.purge_unreferenced_uploads(db, endpoint.project_id)
    return _endpoint_out(db, endpoint)


def delete_endpoint(db: Session, endpoint: ApifoxEndpoint, deleted_by: Optional[int] = None) -> None:
    """软删除：接口连同其下用例一并移入回收站（可还原）。

    接口下任一用例被场景步骤引用则拦截，避免场景步骤运行时找不到用例（镜像用例级删除守卫）。
    """
    _soft_delete_endpoint(db, endpoint)
    endpoint.deleted_by = deleted_by
    db.commit()


def restore_endpoint(db: Session, endpoint: ApifoxEndpoint) -> None:
    """从回收站还原（其下用例随接口一并恢复可见）。"""
    endpoint.deleted_at = None
    db.commit()


def purge_endpoint(db: Session, endpoint: ApifoxEndpoint) -> None:
    """彻底删除：级联清理接口子表 + 其下全部用例（含用例断言/提取/脚本），不可恢复。"""
    for case in case_repo.list_all_cases_by_endpoint(db, endpoint.id):
        case_repo.delete_children(db, case.id)
        script_repo.delete_case_scripts(db, case.id)
        case_repo.delete(db, case)
    repo.delete_endpoint_assertions(db, endpoint.id)
    repo.delete_endpoint_extracts(db, endpoint.id)
    script_repo.delete_endpoint_scripts(db, endpoint.id)
    repo.delete_endpoint(db, endpoint)
    db.commit()


# ---------- 树拖拽重排（原子：一次落库全部 parent/folder + sort_order） ----------
def reorder_tree(db: Session, project_id: int, data: TreeReorderRequest) -> tuple[int, int]:
    project = db.query(Project).filter(Project.id == project_id).with_for_update().first()
    if project is None:
        raise ValueError("项目不存在")
    if project.api_tree_order_version != data.expected_order_version:
        raise OrderVersionConflictError("接口树排序已被其他操作更新，请刷新后重试")

    folders_by_id = {f.id: f for f in repo.list_folders(db, project_id)}
    endpoints_by_id = {e.id: e for e in repo.list_endpoints(db, project_id)}

    for f_item in data.folders:
        folder = folders_by_id.get(f_item.id)
        if folder is None:
            raise ValueError("文件夹不存在或不属于该项目")
        if f_item.parent_id is not None and f_item.parent_id not in folders_by_id:
            raise ValueError("目标父文件夹不存在或不属于该项目")
        folder.parent_id = f_item.parent_id
        folder.sort_order = f_item.sort_order

    if _has_cycle(folders_by_id):
        db.rollback()
        raise ValueError("文件夹移动会形成循环")

    for e_item in data.endpoints:
        endpoint = endpoints_by_id.get(e_item.id)
        if endpoint is None:
            raise ValueError("接口不存在或不属于该项目")
        if e_item.folder_id is not None and e_item.folder_id not in folders_by_id:
            raise ValueError("目标文件夹不存在或不属于该项目")
        endpoint.folder_id = e_item.folder_id
        endpoint.sort_order = e_item.sort_order

    project.api_tree_order_version += 1
    db.commit()
    return project.api_tree_order_version, len(data.folders) + len(data.endpoints)

"""Apifox · OpenAPI 3.x 导入（URL 拉取/粘贴 JSON → 批量生成 endpoint，按 tag 建文件夹）。

导入前先 preview_openapi 出「预览 & 配置」数据，用户勾选接口、选目标目录、定已存在接口的处理方式
（跳过 / 覆盖契约），再由 import_openapi 按 ImportOptions 执行；批量入库单次 commit。
仅支持 OpenAPI 3.x（Swagger 2.0 等由 import_converters 先归一化）。
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
from sqlalchemy.orm import Session

from app.models.apifox.data_model import ApifoxSchema
from app.models.apifox.endpoint import ApifoxEndpoint, ApifoxFolder
from app.repositories.apifox import case_repo, schema_repo
from app.repositories.apifox import endpoint_repo as repo
from app.routers.apifox.schemas import AuthSpec, BodySpec, KvRow, RequestSpec

HTTP_METHODS = ("get", "post", "put", "delete", "patch")
_MAX_SCHEMA_DEPTH = 3
_MAX_MODEL_DEPTH = 6


def fetch_source(
    url: str,
    auth: Optional[Tuple[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    """拉取 URL 原始文本（多格式归一化前不假设是 JSON）；auth=(user,pwd) 走 Basic Auth，
    headers 供 Git PAT 等自定义头；失败抛 ValueError。"""
    try:
        response = httpx.get(url, timeout=10.0, follow_redirects=True, auth=auth, headers=headers)
        response.raise_for_status()
        return response.text
    except (httpx.HTTPError, httpx.InvalidURL) as exc:
        raise ValueError(f"拉取导入源失败: {exc}")


def git_token_headers(token: str) -> Dict[str, str]:
    """Git 私有仓库 raw 文件的鉴权头：GitHub 用 Authorization Bearer，GitLab 用 PRIVATE-TOKEN，
    两者并存互不干扰（对方忽略未知头）。"""
    return {"Authorization": f"Bearer {token}", "PRIVATE-TOKEN": token}


def fetch_openapi(url: str) -> Dict[str, Any]:
    try:
        response = httpx.get(url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
        doc = response.json()
    except (httpx.HTTPError, httpx.InvalidURL) as exc:  # InvalidURL 不属于 HTTPError
        raise ValueError(f"拉取 OpenAPI 失败: {exc}")
    except json.JSONDecodeError:
        raise ValueError("URL 返回内容不是合法 JSON")
    if not isinstance(doc, dict):  # URL 可能返回 JSON 数组/字符串
        raise ValueError("URL 返回内容不是 OpenAPI 文档（应为 JSON 对象）")
    return doc


def parse_content(content: str) -> Dict[str, Any]:
    try:
        doc = json.loads(content)
    except (ValueError, TypeError):
        raise ValueError("粘贴内容不是合法 JSON")
    if not isinstance(doc, dict):
        raise ValueError("OpenAPI 文档必须是 JSON 对象")
    return doc


def validate_openapi(doc: Dict[str, Any]) -> None:
    if not isinstance(doc, dict):
        raise ValueError("OpenAPI 文档必须是 JSON 对象")
    version = str(doc.get("openapi") or "")
    if not version.startswith("3"):
        raise ValueError("仅支持 OpenAPI 3.x（缺少 openapi: 3.x 声明）")
    if not isinstance(doc.get("paths"), dict) or not doc["paths"]:
        raise ValueError("OpenAPI 文档没有 paths")


def _resolve_ref(doc: Dict[str, Any], schema: Dict[str, Any], seen: Set[str]) -> Dict[str, Any]:
    ref = schema.get("$ref")
    if not ref:
        return schema
    if ref in seen:
        return {}
    seen.add(ref)
    node: Any = doc
    for part in ref.lstrip("#/").split("/"):
        if not isinstance(node, dict) or part not in node:
            return {}
        node = node[part]
    return node if isinstance(node, dict) else {}


def _skeleton(doc: Dict[str, Any], schema: Optional[Dict[str, Any]], depth: int = 0,
              seen: Optional[Set[str]] = None) -> Any:
    """按 schema 生成示例骨架（example 优先；$ref 展开防循环；深度护栏）。"""
    if not schema or depth > _MAX_SCHEMA_DEPTH:
        return None
    seen = set(seen or ())
    schema = _resolve_ref(doc, schema, seen)
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    schema_type = schema.get("type")
    if schema_type == "object" or "properties" in schema:
        return {
            key: _skeleton(doc, prop, depth + 1, seen)
            for key, prop in (schema.get("properties") or {}).items()
        }
    if schema_type == "array":
        item = _skeleton(doc, schema.get("items"), depth + 1, seen)
        return [item] if item is not None else []
    if schema_type == "integer" or schema_type == "number":
        return 0
    if schema_type == "boolean":
        return False
    return ""


def _expand_schema(doc: Dict[str, Any], schema: Optional[Dict[str, Any]],
                   depth: int = 0, seen: Optional[Set[str]] = None) -> Dict[str, Any]:
    """把 OpenAPI schema 展开成纯 JSON Schema 结构（$ref 就地内联；防循环+深度护栏）。

    与 _skeleton 不同：这里保留的是 type/properties/items/required 等**结构**（供数据模型编辑器渲染），
    而非示例值。循环引用或超深处降级为 {type: object}。
    """
    if not isinstance(schema, dict) or depth > _MAX_MODEL_DEPTH:
        return {"type": "object"}
    seen = set(seen or ())

    ref = schema.get("$ref")
    if ref:
        if ref in seen:
            return {"type": "object"}
        target = _resolve_ref(doc, schema, set())
        return _expand_schema(doc, target, depth, seen | {ref})

    out: Dict[str, Any] = {}
    for key in ("description", "format", "enum", "default"):
        if key in schema:
            out[key] = schema[key]

    schema_type = schema.get("type")
    if isinstance(schema_type, list):  # OAS 3.1 可空写法 type: ["integer", "null"]
        schema_type = next((t for t in schema_type if t != "null"), None)
    combinator = schema.get("anyOf") or schema.get("oneOf") or schema.get("allOf")

    if schema_type == "object" or "properties" in schema:
        out["type"] = "object"
        out["properties"] = {
            str(key): _expand_schema(doc, prop, depth + 1, seen)
            for key, prop in (schema.get("properties") or {}).items()
        }
        if isinstance(schema.get("required"), list):
            out["required"] = schema["required"]
    elif schema_type == "array":
        out["type"] = "array"
        out["items"] = _expand_schema(doc, schema.get("items") or {}, depth + 1, seen)
    elif schema_type:
        out["type"] = schema_type
    elif isinstance(combinator, list) and combinator:
        # anyOf/oneOf/allOf：取第一个非 null 分支展开（Optional[X] → X），保留父级已收集的元信息
        branch = next(
            (s for s in combinator if isinstance(s, dict) and s.get("type") != "null"), None
        )
        expanded = _expand_schema(doc, branch, depth, seen) if branch else {"type": "object"}
        for key, value in out.items():
            expanded.setdefault(key, value)
        return expanded
    else:
        out["type"] = "object"
    return out


def _param_value(doc: Dict[str, Any], param: Dict[str, Any]) -> str:
    if "example" in param:
        return str(param["example"])
    value = _skeleton(doc, param.get("schema"))
    if value in (None, {}, []):
        return ""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)


# OpenAPI3 类型在 param.schema.type，Swagger2 直接在 param.type；映射到 KvRow.type 支持的集合
_PARAM_TYPES = {"string", "integer", "number", "boolean", "array", "object"}


def _param_type(param: Dict[str, Any]) -> str:
    schema = param.get("schema")
    raw = (schema.get("type") if isinstance(schema, dict) else None) or param.get("type")
    return raw if raw in _PARAM_TYPES else "string"


def _rows_from_params(doc: Dict[str, Any], params: List[Dict[str, Any]], location: str) -> List[KvRow]:
    rows: List[KvRow] = []
    for param in params or []:
        if not isinstance(param, dict):  # 畸形文档里 parameters 可能混入非对象项
            continue
        if param.get("in") != location or not param.get("name"):
            continue
        rows.append(KvRow(
            key=str(param["name"]),
            value=_param_value(doc, param),
            enabled=bool(param.get("required", False)),  # 仅必选参数默认勾选
            desc=str(param.get("description") or ""),
            type=_param_type(param),
        ))
    return rows


def _form_rows(doc: Dict[str, Any], schema: Optional[Dict[str, Any]]) -> List[KvRow]:
    skeleton = _skeleton(doc, schema)
    if not isinstance(skeleton, dict):
        return []
    resolved = _resolve_ref(doc, schema, set()) if isinstance(schema, dict) else {}
    required = set(resolved.get("required") or []) if isinstance(resolved, dict) else set()
    return [
        KvRow(
            key=str(k),
            value=v if isinstance(v, str) else json.dumps(v, ensure_ascii=False),
            enabled=str(k) in required,  # 仅必选字段默认勾选
        )
        for k, v in skeleton.items()
    ]


def _body_spec(doc: Dict[str, Any], request_body: Optional[Dict[str, Any]]) -> BodySpec:
    content = (request_body or {}).get("content") or {}
    if not isinstance(content, dict):
        return BodySpec()

    def _media(key: str) -> Dict[str, Any]:
        media = content.get(key)
        return media if isinstance(media, dict) else {}

    if isinstance(content.get("application/json"), dict):
        media = _media("application/json")
        example = media.get("example")
        if example is None:
            example = _skeleton(doc, media.get("schema"))
        raw = json.dumps(example, ensure_ascii=False, indent=2) if example is not None else ""
        return BodySpec(type="json", raw=raw)
    if isinstance(content.get("application/x-www-form-urlencoded"), dict):
        return BodySpec(type="urlencoded",
                        form=_form_rows(doc, _media("application/x-www-form-urlencoded").get("schema")))
    if isinstance(content.get("multipart/form-data"), dict):
        return BodySpec(type="form-data",
                        form=_form_rows(doc, _media("multipart/form-data").get("schema")))
    return BodySpec()


def parse_openapi(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """解析为待建 endpoint 列表：{name, method, path, folder, description, request_spec}。"""
    endpoints: List[Dict[str, Any]] = []
    for path, path_item in (doc.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        common_params = path_item.get("parameters") or []
        for method in HTTP_METHODS:
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            params = list(common_params) + list(operation.get("parameters") or [])
            tags = operation.get("tags") or []
            spec = RequestSpec(
                query=_rows_from_params(doc, params, "query"),
                path_params=_rows_from_params(doc, params, "path"),
                headers=_rows_from_params(doc, params, "header"),
                body=_body_spec(doc, operation.get("requestBody")),
                auth=AuthSpec(),
            )
            endpoints.append({
                "name": operation.get("summary") or operation.get("operationId")
                        or f"{method.upper()} {path}",
                "method": method.upper(),
                "path": path,
                "folder": str(tags[0]) if tags else None,
                "description": operation.get("description") or None,
                "request_spec": spec,
            })
    return endpoints


# ---------- 请求契约比对（导入覆盖 / 更新同步 / 预览共用） ----------
def load_spec(text: Optional[str]) -> RequestSpec:
    if not text:
        return RequestSpec()
    try:
        return RequestSpec.model_validate_json(text)
    except ValueError:
        return RequestSpec()


def _row_keys(rows) -> frozenset:
    return frozenset(r.key for r in rows if r.key)


def _typed_keys(rows) -> frozenset:
    return frozenset((r.key, r.type) for r in rows if r.key)


def _body_signature(body: BodySpec) -> Tuple[Any, ...]:
    """请求体契约签名：忽略格式差异，识别结构变化（form 键 / json 结构 / 原文）。"""
    if body.type in ("form-data", "urlencoded"):
        return ("form", _row_keys(body.form))
    if body.type == "graphql":
        return ("graphql", (body.graphql_query or "").strip())
    if body.type == "json":
        raw = (body.raw or "").strip()
        try:
            return ("json", json.dumps(json.loads(raw), sort_keys=True, ensure_ascii=False))
        except (ValueError, TypeError):
            return ("json", raw)
    if body.type in ("xml", "raw"):
        return (body.type, (body.raw or "").strip())
    return (body.type,)  # none | binary


def change_labels(new: RequestSpec, old: RequestSpec) -> List[str]:
    """接口契约变更点（只看 import 能表达的结构，忽略示例值/enabled/desc 的本地编辑）。"""
    labels: List[str] = []
    if _typed_keys(new.query) != _typed_keys(old.query):
        labels.append("Query 参数")
    if _typed_keys(new.path_params) != _typed_keys(old.path_params):  # Params 带类型标注，需比 type
        labels.append("Path 参数")
    if _row_keys(new.headers) != _row_keys(old.headers):  # header 无类型语义，只比 key
        labels.append("请求头")
    if _body_signature(new.body) != _body_signature(old.body):
        labels.append("请求体")
    return labels


def apply_contract(ep: ApifoxEndpoint, new_spec: RequestSpec, old_spec: RequestSpec) -> None:
    """只覆盖请求契约字段，保留本地 cookies/auth/settings。"""
    old_spec.query = new_spec.query
    old_spec.path_params = new_spec.path_params
    old_spec.headers = new_spec.headers
    old_spec.body = new_spec.body
    ep.request_spec = old_spec.model_dump_json()


# ---------- 预览 & 选择性导入 ----------
CONFLICT_MODES = ("skip", "overwrite")


def endpoint_key(method: str, path: str) -> str:
    """预览项与勾选项的稳定标识（前端按此回传选中的接口）。"""
    return f"{method.upper()} {path}"


@dataclass
class ImportOptions:
    """用户在「导入预览 & 配置」里做的选择。默认= 全部导入到根目录、已存在的跳过。"""

    # 导入位置：None = 根目录；文档 tag 作为其下的子目录
    target_folder_id: Optional[int] = None
    # 勾选的接口 key（endpoint_key 格式）；None = 不筛选（全部）
    selected_keys: Optional[Set[str]] = None
    # 已存在同 (method, path) 接口时：skip 跳过 / overwrite 覆盖请求契约
    on_conflict: str = "skip"
    # 是否一并导入 components/schemas 为数据模型
    with_schemas: bool = True


def _schema_defs(doc: Dict[str, Any]) -> Dict[str, Any]:
    defs = (doc.get("components") or {}).get("schemas") or {}
    return defs if isinstance(defs, dict) else {}


def preview_openapi(db: Session, project_id: int, doc: Dict[str, Any]) -> Dict[str, Any]:
    """只读预览：按 tag 分组列出待导入接口，并标注库中是否已存在 / 契约是否有变更。不写库。"""
    validate_openapi(doc)
    parsed = parse_openapi(doc)
    existing_by_key = {(e.method.upper(), e.path): e for e in repo.list_endpoints(db, project_id)}

    groups: Dict[str, List[Dict[str, Any]]] = {}
    order: List[str] = []
    exists_count = changed_count = 0
    for item in parsed:
        folder = item["folder"] or ""
        if folder not in groups:
            groups[folder] = []
            order.append(folder)
        ep = existing_by_key.get((item["method"], item["path"]))
        changed = bool(ep is not None and change_labels(item["request_spec"], load_spec(ep.request_spec)))
        exists_count += 1 if ep is not None else 0
        changed_count += 1 if changed else 0
        groups[folder].append({
            "key": endpoint_key(item["method"], item["path"]),
            "name": item["name"],
            "method": item["method"],
            "path": item["path"],
            "folder": folder,
            "exists": ep is not None,
            "changed": changed,
        })

    info = doc.get("info") if isinstance(doc.get("info"), dict) else {}
    return {
        "title": str((info or {}).get("title") or "导入数据"),
        "folders": [{"name": name, "endpoints": groups[name]} for name in order],
        "total": len(parsed),
        "exists_count": exists_count,
        "changed_count": changed_count,
        "schemas_total": len(_schema_defs(doc)),
        "schemas_new": count_new_schemas(db, project_id, doc),
    }


def _resolve_folder_id(
    db: Session,
    project_id: int,
    folder_name: Optional[str],
    folder_by_name: Dict[str, ApifoxFolder],
    parent_id: Optional[int] = None,
) -> Tuple[Optional[int], bool]:
    """按 tag 名在 parent_id 下 get-or-create 文件夹；返回 (folder_id, 是否新建)。
    无 tag 的接口直接落在 parent_id（目标目录，None 即根目录）。"""
    if not folder_name:
        return parent_id, False
    folder = folder_by_name.get(folder_name)
    if folder is None:
        folder = ApifoxFolder(project_id=project_id, name=folder_name, parent_id=parent_id)
        repo.create_folder(db, folder)
        folder_by_name[folder_name] = folder
        return folder.id, True
    return folder.id, False


def create_endpoint_from_item(
    db: Session,
    project_id: int,
    item: Dict[str, Any],
    folder_by_name: Dict[str, ApifoxFolder],
    parent_id: Optional[int] = None,
) -> bool:
    """按解析项建接口（folder get-or-create）；返回是否新建了文件夹。导入与更新同步共用。"""
    folder_id, folder_created = _resolve_folder_id(
        db, project_id, item["folder"], folder_by_name, parent_id
    )
    repo.create_endpoint(db, ApifoxEndpoint(
        project_id=project_id,
        folder_id=folder_id,
        name=item["name"][:200],
        method=item["method"],
        path=item["path"][:500],
        request_spec=item["request_spec"].model_dump_json(),
        description=item["description"],
    ))
    return folder_created


def _folder_index(
    db: Session, project_id: int, options: ImportOptions
) -> Dict[str, ApifoxFolder]:
    """目标目录下的同名文件夹索引（tag → folder），顺带校验目标目录属于本项目。"""
    folders = repo.list_folders(db, project_id)
    if options.target_folder_id is not None and all(
        f.id != options.target_folder_id for f in folders
    ):
        raise ValueError("目标目录不存在或不属于当前项目")
    return {f.name: f for f in folders if f.parent_id == options.target_folder_id}


def import_openapi(
    db: Session,
    project_id: int,
    doc: Dict[str, Any],
    options: Optional[ImportOptions] = None,
) -> Dict[str, int]:
    """导入编排：按勾选项过滤 + 已存在项按策略跳过/覆盖 + tag 目录建在目标目录下，单次 commit。"""
    options = options or ImportOptions()
    if options.on_conflict not in CONFLICT_MODES:
        raise ValueError("已存在接口的处理方式仅支持 skip / overwrite")
    validate_openapi(doc)
    parsed = parse_openapi(doc)
    if options.selected_keys is not None:
        parsed = [
            it for it in parsed if endpoint_key(it["method"], it["path"]) in options.selected_keys
        ]

    existing: Dict[Tuple[str, str], ApifoxEndpoint] = {
        (e.method.upper(), e.path): e for e in repo.list_endpoints(db, project_id)
    }
    folder_by_name = _folder_index(db, project_id, options)

    created = updated = skipped = folders_created = 0
    seen: Set[Tuple[str, str]] = set()
    for item in parsed:
        key = (item["method"], item["path"])
        ep = existing.get(key)
        if ep is not None or key in seen:
            # 已存在：按用户选择跳过或覆盖请求契约（契约无变化时不算更新）
            if ep is not None and options.on_conflict == "overwrite":
                old_spec = load_spec(ep.request_spec)
                if change_labels(item["request_spec"], old_spec):
                    apply_contract(ep, item["request_spec"], old_spec)
                    if case_repo.list_cases(db, ep.id):
                        ep.cases_stale = True  # 有用例则标记待复核，供树上提示
                    updated += 1
                    continue
            skipped += 1
            continue
        if create_endpoint_from_item(
            db, project_id, item, folder_by_name, options.target_folder_id
        ):
            folders_created += 1
        seen.add(key)
        created += 1

    schemas_created = import_schemas(db, project_id, doc) if options.with_schemas else 0

    db.commit()
    return {
        "total": len(parsed),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "folders_created": folders_created,
        "schemas_created": schemas_created,
    }


def count_new_schemas(db: Session, project_id: int, doc: Dict[str, Any]) -> int:
    """只读统计 components/schemas 中的新增数量（供 diff 预览，不写库）。

    与 import_schemas 一致：大小写不敏感去重 + 文档内变体也只计一次，预览数=实际新建数。
    """
    components_schemas = (doc.get("components") or {}).get("schemas") or {}
    if not isinstance(components_schemas, dict):
        return 0
    existing_lower = {s.name.lower() for s in schema_repo.list_schemas(db, project_id)}
    seen: set[str] = set()
    count = 0
    for name, sd in components_schemas.items():
        key = str(name)[:200].lower()
        if isinstance(sd, dict) and key not in existing_lower and key not in seen:
            seen.add(key)
            count += 1
    return count


def import_schemas(db: Session, project_id: int, doc: Dict[str, Any]) -> int:
    """把 components/schemas 导入为数据模型（同名去重不覆盖；$ref 就地展开）。

    去重**大小写不敏感**：对齐 MySQL 唯一索引 (project_id, name) 的 ci 语义，
    避免文档里 `Foo`/`foo` 或库中已有大小写变体时撞 Duplicate entry。
    """
    components_schemas = (doc.get("components") or {}).get("schemas") or {}
    if not isinstance(components_schemas, dict):
        return 0
    existing_lower = {s.name.lower() for s in schema_repo.list_schemas(db, project_id)}
    schemas_created = 0
    for name, schema_def in components_schemas.items():
        safe_name = str(name)[:200]
        key = safe_name.lower()
        if not isinstance(schema_def, dict) or key in existing_lower:
            continue
        expanded = _expand_schema(doc, schema_def)
        schema_repo.add(db, ApifoxSchema(
            project_id=project_id,
            name=safe_name,
            json_schema=json.dumps(expanded, ensure_ascii=False, indent=2),
            description=schema_def.get("description"),
        ))
        existing_lower.add(key)
        schemas_created += 1
    return schemas_created

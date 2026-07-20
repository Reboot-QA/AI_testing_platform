"""Apifox · OpenAPI 3.x 导入（URL 拉取/粘贴 JSON → 批量生成 endpoint，按 tag 建文件夹）。

同 (method, path) 已存在则跳过；批量入库单次 commit。仅支持 OpenAPI 3.x（Swagger 2.0 后续）。
"""

import json
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
from sqlalchemy.orm import Session

from app.models.apifox.data_model import ApifoxSchema
from app.models.apifox.endpoint import ApifoxEndpoint, ApifoxFolder
from app.repositories.apifox import endpoint_repo as repo
from app.repositories.apifox import schema_repo
from app.routers.apifox.schemas import AuthSpec, BodySpec, KvRow, RequestSpec

HTTP_METHODS = ("get", "post", "put", "delete", "patch")
_MAX_SCHEMA_DEPTH = 3
_MAX_MODEL_DEPTH = 6


def fetch_source(url: str) -> str:
    """拉取 URL 原始文本（多格式归一化前不假设是 JSON）；失败抛 ValueError。"""
    try:
        response = httpx.get(url, timeout=10.0, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except (httpx.HTTPError, httpx.InvalidURL) as exc:
        raise ValueError(f"拉取导入源失败: {exc}")


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


def _resolve_folder_id(
    db: Session, project_id: int, folder_name: Optional[str], folder_by_name: Dict[str, ApifoxFolder]
) -> Tuple[Optional[int], bool]:
    """按 tag 名 get-or-create 顶层文件夹；返回 (folder_id, 是否新建)。"""
    if not folder_name:
        return None, False
    folder = folder_by_name.get(folder_name)
    if folder is None:
        folder = ApifoxFolder(project_id=project_id, name=folder_name)
        repo.create_folder(db, folder)
        folder_by_name[folder_name] = folder
        return folder.id, True
    return folder.id, False


def create_endpoint_from_item(
    db: Session, project_id: int, item: Dict[str, Any], folder_by_name: Dict[str, ApifoxFolder]
) -> bool:
    """按解析项建接口（folder get-or-create）；返回是否新建了文件夹。导入与更新同步共用。"""
    folder_id, folder_created = _resolve_folder_id(db, project_id, item["folder"], folder_by_name)
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


def import_openapi(db: Session, project_id: int, doc: Dict[str, Any]) -> Dict[str, int]:
    """导入编排：跳重(method,path) + 按 tag get-or-create 文件夹 + 批量入库单次 commit。"""
    validate_openapi(doc)
    parsed = parse_openapi(doc)

    existing: Set[Tuple[str, str]] = {
        (e.method.upper(), e.path) for e in repo.list_endpoints(db, project_id)
    }
    folder_by_name: Dict[str, ApifoxFolder] = {
        f.name: f for f in repo.list_folders(db, project_id) if f.parent_id is None
    }

    created = skipped = folders_created = 0
    for item in parsed:
        if (item["method"], item["path"]) in existing:
            skipped += 1
            continue
        if create_endpoint_from_item(db, project_id, item, folder_by_name):
            folders_created += 1
        existing.add((item["method"], item["path"]))
        created += 1

    schemas_created = import_schemas(db, project_id, doc)

    db.commit()
    return {
        "total": len(parsed),
        "created": created,
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

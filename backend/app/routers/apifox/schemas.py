"""Apifox 接口管理 · 请求/响应契约。

request_spec 为结构化 JSON（请求数据，非行为）；DB 存 Text，service 负责 dump/load。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- request_spec 子结构 ----------
class KvRow(BaseModel):
    key: str = ""
    value: str = ""
    enabled: bool = True
    desc: str = ""
    type: str = "string"  # 参数类型标注（string/integer/number/boolean/array/object/file），仅 Params 用


class BodySpec(BaseModel):
    type: str = "none"  # none|json|xml|form-data|urlencoded|raw|graphql|binary
    raw: str = ""  # json/xml/raw 共用
    form: List[KvRow] = Field(default_factory=list)
    graphql_query: str = ""
    graphql_variables: str = ""  # JSON 文本
    file_id: Optional[int] = None  # binary：引用 apifox_upload_files.id
    file_name: str = ""  # binary：展示用文件名（发送时按 file_id 取字节）


class AuthSpec(BaseModel):
    type: str = "none"  # none|bearer|basic
    token: str = ""
    username: str = ""
    password: str = ""


class RequestSettings(BaseModel):
    timeout_ms: Optional[int] = None  # None 或 <=0 → 用平台默认超时（HTTP_TIMEOUT）
    verify_ssl: bool = True
    follow_redirects: bool = True


class RequestSpec(BaseModel):
    query: List[KvRow] = Field(default_factory=list)
    path_params: List[KvRow] = Field(default_factory=list)
    headers: List[KvRow] = Field(default_factory=list)
    cookies: List[KvRow] = Field(default_factory=list)
    body: BodySpec = Field(default_factory=BodySpec)
    auth: AuthSpec = Field(default_factory=AuthSpec)
    settings: RequestSettings = Field(default_factory=RequestSettings)


# ---------- 处理器行（接口级与用例级共用，case_schemas 从此导入避免循环依赖） ----------
class AssertionRow(BaseModel):
    type: str = "status_code"  # status_code|json_path|header|contains|response_time
    path: Optional[str] = None
    operator: str = "eq"  # eq|neq|contains|not_contains|gt|gte|lt|lte|regex|exists
    expected: Optional[str] = None
    enabled: bool = True


class ExtractRow(BaseModel):
    var_name: str
    source: str = "response_json"
    path: Optional[str] = None
    scope: str = "temporary"  # temporary|environment|global
    enabled: bool = True


class CaseScriptRef(BaseModel):
    """前后置对项目脚本库的引用（用例与接口共用）。"""

    script_id: int
    enabled: bool = True


class CaseScriptOut(CaseScriptRef):
    script_name: str = ""
    script_lang: str = ""


# ---------- folder ----------
class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_id: Optional[int] = None


class FolderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


class FolderOut(BaseModel):
    id: int
    project_id: int
    parent_id: Optional[int] = None
    name: str
    sort_order: int


# ---------- endpoint ----------
class EndpointCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    method: str = "GET"
    path: str = ""
    folder_id: Optional[int] = None
    server_name: Optional[str] = None
    request_spec: RequestSpec = Field(default_factory=RequestSpec)
    description: Optional[str] = None
    response_schema_id: Optional[int] = None
    contract_strict: bool = False
    assertions: List[AssertionRow] = Field(default_factory=list)
    extracts: List[ExtractRow] = Field(default_factory=list)
    pre_scripts: List[CaseScriptRef] = Field(default_factory=list)
    post_scripts: List[CaseScriptRef] = Field(default_factory=list)


class EndpointUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    method: Optional[str] = None
    path: Optional[str] = None
    folder_id: Optional[int] = None
    server_name: Optional[str] = None
    request_spec: Optional[RequestSpec] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    response_schema_id: Optional[int] = None
    contract_strict: Optional[bool] = None
    assertions: Optional[List[AssertionRow]] = None
    extracts: Optional[List[ExtractRow]] = None
    pre_scripts: Optional[List[CaseScriptRef]] = None
    post_scripts: Optional[List[CaseScriptRef]] = None
    # 乐观锁：客户端读取时的版本；不一致则 409（None=不校验，向后兼容）
    expected_version: Optional[int] = None


class EndpointBrief(BaseModel):
    """树列表用（不含完整 request_spec）。"""

    id: int
    folder_id: Optional[int] = None
    name: str
    method: str
    path: str
    sort_order: int


class EndpointOut(BaseModel):
    id: int
    project_id: int
    folder_id: Optional[int] = None
    name: str
    method: str
    path: str
    server_name: Optional[str] = None
    request_spec: RequestSpec
    description: Optional[str] = None
    sort_order: int
    response_schema_id: Optional[int] = None
    contract_strict: bool = False
    assertions: List[AssertionRow] = Field(default_factory=list)
    extracts: List[ExtractRow] = Field(default_factory=list)
    pre_scripts: List[CaseScriptOut] = Field(default_factory=list)
    post_scripts: List[CaseScriptOut] = Field(default_factory=list)
    version: int = 1
    created_at: datetime
    updated_at: datetime


# ---------- 树拖拽重排 ----------
class ReorderFolder(BaseModel):
    id: int
    parent_id: Optional[int] = None
    sort_order: int = 0


class ReorderEndpoint(BaseModel):
    id: int
    folder_id: Optional[int] = None
    sort_order: int = 0


class TreeReorderRequest(BaseModel):
    folders: List[ReorderFolder] = Field(default_factory=list)
    endpoints: List[ReorderEndpoint] = Field(default_factory=list)


# ---------- 更新 Swagger（增量同步）：先出 diff 预览，再确认应用 ----------
class ImportDiffEndpoint(BaseModel):
    """新增项：新 spec 有、库里无。"""

    method: str
    path: str
    name: str


class ImportChangedEndpoint(BaseModel):
    """变更项：两边都有但接口定义不同；受影响用例仅告知（不自动改）。"""

    endpoint_id: int
    method: str
    path: str
    name: str
    changes: List[str] = Field(default_factory=list)  # 名称/描述/参数/请求体
    affected_cases: List[str] = Field(default_factory=list)  # 引用该接口的用例名（自查提示）


class ImportCaseRef(BaseModel):
    """被移除接口下、被场景/套件引用的用例（修改提示锚点）。"""

    case_id: int
    case_name: str
    scenarios: List[str] = Field(default_factory=list)
    suites: List[str] = Field(default_factory=list)


class ImportRemovedEndpoint(BaseModel):
    """移除项：库里有、新 spec 无。referenced=True 表示有用例被引用，不自动删。"""

    endpoint_id: int
    method: str
    path: str
    name: str
    case_count: int = 0
    referenced: bool = False
    references: List[ImportCaseRef] = Field(default_factory=list)


class ImportDiffOut(BaseModel):
    added: List[ImportDiffEndpoint] = Field(default_factory=list)
    changed: List[ImportChangedEndpoint] = Field(default_factory=list)
    removed: List[ImportRemovedEndpoint] = Field(default_factory=list)
    schemas_added: int = 0


class ImportSyncReport(BaseModel):
    added: int = 0
    updated: int = 0
    deleted: int = 0
    kept_referenced: int = 0  # 有引用被保留的移除项
    schemas_created: int = 0
    warnings: List[str] = Field(default_factory=list)  # 被引用移除项的修改提示

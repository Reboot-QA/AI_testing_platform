"""Apifox 接口用例 · 请求/响应契约。

断言/提取为行；请求(复用 RequestSpec)/用例变量/数据驱动为结构化 JSON。脚本不在此（后续脚本库）。
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.routers.apifox.schemas import KvRow, RequestSpec


class AssertionRow(BaseModel):
    type: str = "status_code"  # status_code|json_path|header|contains|response_time
    path: Optional[str] = None
    expected: Optional[str] = None
    enabled: bool = True


class ExtractRow(BaseModel):
    var_name: str
    source: str = "response_json"
    path: Optional[str] = None
    scope: str = "temporary"  # temporary|environment|global
    enabled: bool = True


class DataDriveRow(BaseModel):
    name: str = ""
    enabled: bool = True
    values: Dict[str, str] = Field(default_factory=dict)


class DataDrive(BaseModel):
    enabled: bool = False
    rows: List[DataDriveRow] = Field(default_factory=list)


class CaseScriptRef(BaseModel):
    """用例前后置对项目脚本库的引用。"""

    script_id: int
    enabled: bool = True


class CaseScriptOut(CaseScriptRef):
    script_name: str = ""
    script_lang: str = ""


class CaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    request_spec: RequestSpec = Field(default_factory=RequestSpec)
    variables: List[KvRow] = Field(default_factory=list)
    data_drive: DataDrive = Field(default_factory=DataDrive)
    assertions: List[AssertionRow] = Field(default_factory=list)
    extracts: List[ExtractRow] = Field(default_factory=list)
    pre_scripts: List[CaseScriptRef] = Field(default_factory=list)
    post_scripts: List[CaseScriptRef] = Field(default_factory=list)


class CaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    request_spec: Optional[RequestSpec] = None
    variables: Optional[List[KvRow]] = None
    data_drive: Optional[DataDrive] = None
    assertions: Optional[List[AssertionRow]] = None
    extracts: Optional[List[ExtractRow]] = None
    pre_scripts: Optional[List[CaseScriptRef]] = None
    post_scripts: Optional[List[CaseScriptRef]] = None
    sort_order: Optional[int] = None


class CaseBrief(BaseModel):
    id: int
    endpoint_id: int
    name: str
    sort_order: int


class ProjectCaseBrief(BaseModel):
    """项目全量用例（带接口信息），场景步骤选择器数据源。"""

    id: int
    name: str
    endpoint_id: int
    endpoint_name: str
    endpoint_method: str


class CaseOut(BaseModel):
    id: int
    project_id: int
    endpoint_id: int
    name: str
    request_spec: RequestSpec
    variables: List[KvRow]
    data_drive: DataDrive
    assertions: List[AssertionRow]
    extracts: List[ExtractRow]
    pre_scripts: List[CaseScriptOut] = Field(default_factory=list)
    post_scripts: List[CaseScriptOut] = Field(default_factory=list)
    sort_order: int
    created_at: datetime
    updated_at: datetime

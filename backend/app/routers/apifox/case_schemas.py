"""Apifox 接口用例 · 请求/响应契约。

断言/提取为行；请求(复用 RequestSpec)/用例变量/数据驱动为结构化 JSON。脚本不在此（后续脚本库）。
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.routers.apifox.schemas import (
    AssertionRow,
    CaseScriptOut,
    CaseScriptRef,
    ExtractRow,
    KvRow,
    RequestSpec,
)

__all__ = [
    "AssertionRow",
    "ExtractRow",
    "CaseScriptRef",
    "CaseScriptOut",
    "DataDriveRow",
    "DataDrive",
    "CaseCreate",
    "AiGenCategory",
    "AiGenerateRequest",
    "AiGenerateResult",
    "CaseUpdate",
    "CaseBrief",
    "ProjectCaseBrief",
    "CaseOut",
]


class DataDriveRow(BaseModel):
    name: str = ""
    enabled: bool = True
    values: Dict[str, str] = Field(default_factory=dict)


class DataDrive(BaseModel):
    enabled: bool = False
    # inline（内联行，默认）| dataset（引用项目级数据集，按其行迭代）
    source: str = "inline"
    dataset_id: Optional[int] = None
    rows: List[DataDriveRow] = Field(default_factory=list)


CASE_CATEGORIES = {"positive", "negative", "boundary", "security", "other"}


class CaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = "other"  # positive|negative|boundary|security|other
    request_spec: RequestSpec = Field(default_factory=RequestSpec)
    variables: List[KvRow] = Field(default_factory=list)
    data_drive: DataDrive = Field(default_factory=DataDrive)
    assertions: List[AssertionRow] = Field(default_factory=list)
    extracts: List[ExtractRow] = Field(default_factory=list)
    pre_scripts: List[CaseScriptRef] = Field(default_factory=list)
    post_scripts: List[CaseScriptRef] = Field(default_factory=list)


class AiGenCategory(BaseModel):
    category: Literal["positive", "negative", "boundary", "security"]
    count: Optional[int] = Field(default=None, ge=1, le=20)  # None=由 AI 按接口复杂度自动决定


class AiGenerateRequest(BaseModel):
    categories: List[AiGenCategory] = Field(min_length=1)
    provider_id: Optional[int] = None


class AiGenerateResult(BaseModel):
    mode: str  # mock|llm
    cases: List[CaseCreate]


class CaseUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category: Optional[str] = None
    request_spec: Optional[RequestSpec] = None
    variables: Optional[List[KvRow]] = None
    data_drive: Optional[DataDrive] = None
    assertions: Optional[List[AssertionRow]] = None
    extracts: Optional[List[ExtractRow]] = None
    pre_scripts: Optional[List[CaseScriptRef]] = None
    post_scripts: Optional[List[CaseScriptRef]] = None
    sort_order: Optional[int] = None
    # 乐观锁：客户端读取时的版本；服务端不一致则 409（None=不校验，向后兼容）
    expected_version: Optional[int] = None


class CaseBrief(BaseModel):
    id: int
    endpoint_id: int
    name: str
    category: str = "other"
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
    category: str = "other"
    request_spec: RequestSpec
    variables: List[KvRow]
    data_drive: DataDrive
    assertions: List[AssertionRow]
    extracts: List[ExtractRow]
    pre_scripts: List[CaseScriptOut] = Field(default_factory=list)
    post_scripts: List[CaseScriptOut] = Field(default_factory=list)
    sort_order: int
    version: int = 1
    created_at: datetime
    updated_at: datetime

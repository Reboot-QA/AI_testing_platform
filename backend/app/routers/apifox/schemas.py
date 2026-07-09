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


class BodySpec(BaseModel):
    type: str = "none"  # none|json|form-data|urlencoded|raw
    raw: str = ""
    form: List[KvRow] = Field(default_factory=list)


class AuthSpec(BaseModel):
    type: str = "none"  # none|bearer|basic
    token: str = ""
    username: str = ""
    password: str = ""


class RequestSpec(BaseModel):
    query: List[KvRow] = Field(default_factory=list)
    path_params: List[KvRow] = Field(default_factory=list)
    headers: List[KvRow] = Field(default_factory=list)
    body: BodySpec = Field(default_factory=BodySpec)
    auth: AuthSpec = Field(default_factory=AuthSpec)


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
    request_spec: RequestSpec = Field(default_factory=RequestSpec)
    description: Optional[str] = None


class EndpointUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    method: Optional[str] = None
    path: Optional[str] = None
    folder_id: Optional[int] = None
    request_spec: Optional[RequestSpec] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None


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
    request_spec: RequestSpec
    description: Optional[str] = None
    sort_order: int
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

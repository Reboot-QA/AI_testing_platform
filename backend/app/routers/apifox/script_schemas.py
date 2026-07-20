"""Apifox 脚本库 · 请求/响应契约。"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ScriptDebugIn(BaseModel):
    phase: Literal["pre", "post"] = "pre"
    lang: str = "javascript"
    content: str = ""
    variables: Dict[str, str] = Field(default_factory=dict)
    # post 阶段的响应上下文（pre 忽略）
    response_body: str = ""
    response_status: int = 200
    response_headers: Dict[str, Any] = Field(default_factory=dict)


class ScriptDebugOut(BaseModel):
    status: str  # passed | failed
    logs: List[str] = Field(default_factory=list)
    variables: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None


class DebugPresetIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phase: Literal["pre", "post"] = "pre"
    variables: Dict[str, str] = Field(default_factory=dict)
    response_status: int = 200
    response_body: str = ""


class DebugPresetOut(BaseModel):
    id: int
    name: str
    phase: str
    variables: Dict[str, str] = Field(default_factory=dict)
    response_status: int
    response_body: str


class ScriptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    lang: str = "javascript"  # javascript | python
    content: str = ""
    description: Optional[str] = None


class ScriptUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    lang: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    # 乐观锁：客户端读取时的版本；不一致则 409（None=不校验，向后兼容）
    expected_version: Optional[int] = None


class ScriptBrief(BaseModel):
    id: int
    name: str
    lang: str
    description: Optional[str] = None
    sort_order: int


class ScriptOut(BaseModel):
    id: int
    project_id: int
    name: str
    lang: str
    content: str
    description: Optional[str] = None
    sort_order: int
    version: int = 1
    created_at: datetime
    updated_at: datetime

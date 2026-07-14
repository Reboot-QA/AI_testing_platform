"""Apifox 脚本库 · 请求/响应契约。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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

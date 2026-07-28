"""Apifox SQL 脚本库 · 请求/响应契约（对齐 Script）。"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.constants.limits import DESC_MAX_LEN, TITLE_MAX_LEN


class SqlScriptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=TITLE_MAX_LEN)
    content: str = Field(min_length=1)  # SQL 正文必填非空
    description: Optional[str] = Field(default=None, max_length=DESC_MAX_LEN)
    sort_order: Optional[int] = None


class SqlScriptUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=TITLE_MAX_LEN)
    content: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=DESC_MAX_LEN)
    sort_order: Optional[int] = None
    # 乐观锁：客户端读取时的版本；不一致则 409（None=不校验，向后兼容）
    expected_version: Optional[int] = None


class SqlScriptBrief(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    sort_order: int


class SqlScriptOut(BaseModel):
    id: int
    project_id: int
    name: str
    content: str
    description: Optional[str] = None
    sort_order: int
    version: int = 1
    created_at: datetime
    updated_at: datetime


class SqlScriptDebugIn(BaseModel):
    content: str = Field(min_length=1)  # SQL 正文必填非空
    connection_id: int  # 项目环境数据库连接 id（须属可访问项目）


class SqlScriptDebugOut(BaseModel):
    status: str  # passed | failed
    row_count: int = 0
    preview_rows: List[Dict[str, Any]] = Field(default_factory=list)  # 最多 100 行
    error_message: Optional[str] = None

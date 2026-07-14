"""Apifox 数据模型(Schema) · 请求/响应契约。json_schema 为原始 JSON 文本（service 校验合法性）。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SchemaCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    json_schema: str = "{}"
    description: Optional[str] = None


class SchemaUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    json_schema: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    # 乐观锁：客户端读取时的版本；不一致则 409（None=不校验，向后兼容）
    expected_version: Optional[int] = None


class SchemaBrief(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    sort_order: int
    # 被引用总数（接口响应契约 + 其他模型 $ref），删除/改名保护依据
    ref_count: int = 0


class SchemaOut(BaseModel):
    id: int
    project_id: int
    name: str
    json_schema: str
    description: Optional[str] = None
    sort_order: int
    version: int = 1
    created_at: datetime
    updated_at: datetime
    # 跨模型 $ref 全部内联后的自包含 schema（供前端预览「有效结构」）
    resolved_schema: str = "{}"

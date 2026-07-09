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


class SchemaBrief(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    sort_order: int


class SchemaOut(BaseModel):
    id: int
    project_id: int
    name: str
    json_schema: str
    description: Optional[str] = None
    sort_order: int
    created_at: datetime
    updated_at: datetime

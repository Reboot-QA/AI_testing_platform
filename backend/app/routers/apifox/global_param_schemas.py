"""Apifox 全局参数 · 请求/响应契约。"""

from typing import Optional

from pydantic import BaseModel, Field


class GlobalParamCreate(BaseModel):
    location: str = "header"  # header | query | cookie | body
    key: str = Field(min_length=1, max_length=200)
    value: Optional[str] = None
    enabled: bool = True


class GlobalParamUpdate(BaseModel):
    location: Optional[str] = None
    key: Optional[str] = Field(default=None, min_length=1, max_length=200)
    value: Optional[str] = None
    enabled: Optional[bool] = None
    sort_order: Optional[int] = None


class GlobalParamOut(BaseModel):
    id: int
    project_id: int
    location: str
    key: str
    value: Optional[str] = None
    enabled: bool
    sort_order: int

"""Apifox 测试套件 · 请求/响应契约。

套件项(item)引用一个用例(case)或场景(scenario)；ItemOut 带展示字段（名称/图标信息）。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SuiteItemIn(BaseModel):
    target_type: str  # case | scenario
    target_id: int
    enabled: bool = True


class SuiteItemOut(SuiteItemIn):
    # 展示字段（服务端填充）
    target_name: str = ""
    # case 项：所属接口方法/路径；scenario 项为空
    endpoint_method: str = ""
    endpoint_path: str = ""


class SuiteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    items: List[SuiteItemIn] = Field(default_factory=list)


class SuiteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    items: Optional[List[SuiteItemIn]] = None
    sort_order: Optional[int] = None
    # 乐观锁：客户端读取时的版本；不一致则 409（None=不校验，向后兼容）
    expected_version: Optional[int] = None


class SuiteBrief(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    item_count: int = 0
    sort_order: int


class SuiteOut(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    items: List[SuiteItemOut]
    sort_order: int
    version: int = 1
    created_at: datetime
    updated_at: datetime

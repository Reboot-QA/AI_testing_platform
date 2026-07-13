"""Apifox 项目级数据集 · 请求/响应契约。"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DatasetRowIn(BaseModel):
    values: Dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    columns: List[str] = Field(default_factory=list)
    rows: List[DatasetRowIn] = Field(default_factory=list)


class DatasetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[DatasetRowIn]] = None
    sort_order: Optional[int] = None


class DatasetBrief(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    column_count: int = 0
    row_count: int = 0
    sort_order: int
    # 被多少用例数据驱动引用（删除保护依据）
    ref_count: int = 0


class DatasetOut(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str] = None
    columns: List[str]
    rows: List[DatasetRowIn]
    sort_order: int
    created_at: datetime
    updated_at: datetime

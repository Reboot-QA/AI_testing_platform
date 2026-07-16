"""Apifox AI 生成任务 · 请求/响应契约。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.routers.apifox.case_schemas import AiGenCategory, CaseCreate


class AiGenTaskCreate(BaseModel):
    endpoint_ids: List[int] = Field(min_length=1)
    categories: List[AiGenCategory] = Field(min_length=1)
    provider_id: Optional[int] = None


class AiGenTaskItemOut(BaseModel):
    id: int
    endpoint_id: int
    endpoint_name: str
    endpoint_method: str
    status: str
    generated_count: int
    applied_count: int
    error: Optional[str] = None
    cases: List[CaseCreate] = []  # 生成的用例预览（未入库），供前端勾选后 apply


class AiGenTaskOut(BaseModel):
    id: int
    project_id: int
    status: str
    mode: Optional[str] = None
    provider_id: Optional[int] = None
    total_items: int
    done_items: int
    error: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
    items: List[AiGenTaskItemOut] = []


class AiGenTaskBrief(BaseModel):
    id: int
    status: str
    total_items: int
    done_items: int
    created_at: datetime


class AiGenApplyRequest(BaseModel):
    # 要入库的用例在该 item.cases 中的下标；缺省/空则全部入库
    indexes: Optional[List[int]] = None


class AiGenApplyResult(BaseModel):
    created: int
    failed: List[str] = []

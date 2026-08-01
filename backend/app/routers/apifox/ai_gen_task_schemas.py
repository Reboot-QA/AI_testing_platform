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
    applied_cases: List[CaseCreate] = []  # 已从预览入库的用例快照，供「已入库」Tab 查看
    discarded_cases: List[CaseCreate] = []  # 已从预览废弃、未入库，供「废弃」Tab 查看


class AiGenTaskOut(BaseModel):
    id: int
    project_id: int
    status: str
    mode: Optional[str] = None
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None  # provider 配置名称（兼容）
    model_label: str = ""  # 详情/列表「模型」：仅 model 标识
    categories: List[AiGenCategory] = []  # 生成时选的类别配置（含数量），详情信息区展示
    creator_name: Optional[str] = None
    total_items: int
    done_items: int
    error: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None
    items: List[AiGenTaskItemOut] = []


class AiGenTaskBrief(BaseModel):
    id: int
    status: str
    mode: Optional[str] = None  # llm|mock，跑起来才定
    target: Optional[str] = None  # 单接口任务=method+path；批量为空（前端展示"批量·N接口"）
    categories: List[str] = []  # 选中的类别值（positive/negative/...），列表摘要用
    generated_total: int = 0  # 该任务已生成用例总数（Σ 各接口）
    applied_total: int = 0  # 已入库用例总数（Σ 各接口 applied_count）
    model_label: str = ""  # 列表「模型」：仅 model 标识
    creator_name: Optional[str] = None
    total_items: int
    done_items: int
    created_at: datetime
    finished_at: Optional[datetime] = None


class AiGenTaskPageOut(BaseModel):
    items: List[AiGenTaskBrief]
    total: int
    page: int
    page_size: int


class AiGenApplyRequest(BaseModel):
    # 要入库的用例在该 item.cases 中的下标；缺省/空则全部入库
    indexes: Optional[List[int]] = None


class AiGenApplyResult(BaseModel):
    created: int
    failed: List[str] = []
    skipped: int = 0  # 同名用例已存在，跳过未重复创建的条数


class AiGenDiscardResult(BaseModel):
    discarded: int  # 从预览中移除的条数（未入库）


class AiGenBatchApplyItem(BaseModel):
    item_id: int
    # 要入库的用例下标；缺省/空则该项全部入库
    indexes: Optional[List[int]] = None


class AiGenBatchApplyRequest(BaseModel):
    items: List[AiGenBatchApplyItem]


class AiGenBatchApplyResult(BaseModel):
    created: int
    skipped: int = 0
    failed: List[str] = []
    applied_items: int = 0
    task: AiGenTaskOut  # 入库后最新任务（含各项 applied_count），省去前端再查一次

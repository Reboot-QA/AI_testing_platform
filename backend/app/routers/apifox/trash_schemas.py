"""Apifox 回收站 · Pydantic schema（软删除的场景/套件/用例统一视图）。"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

# 回收站支持的实体类型（场景/套件/用例/单接口）
TrashKind = Literal["scenario", "suite", "case", "endpoint"]


class TrashItem(BaseModel):
    kind: TrashKind
    id: int
    name: str
    deleted_at: datetime
    # 到期彻底清理时间（= deleted_at + 保留期）
    expires_at: datetime
    # 剩余保留天数（后端算，deleted_at 与 now 同一时钟，避免前端跨时区解析偏差）；0=即将清理
    remaining_days: int = 0
    # 副信息：场景=优先级；用例=所属接口(method + name)；套件=None；接口=method + path
    detail: Optional[str] = None
    # 操作人（删除者登录账号 username；历史无 deleted_by 时为 None）
    operator: Optional[str] = None


class TrashBatchItemIn(BaseModel):
    kind: TrashKind
    id: int


class TrashBatchIn(BaseModel):
    items: list[TrashBatchItemIn]


class TrashBatchOut(BaseModel):
    succeeded: int
    failed: int
    errors: list[str] = []


class TrashRestoreOut(BaseModel):
    entity_type: TrashKind
    entity_id: int
    restored_at: datetime
    version: Optional[int] = None


class TrashPageOut(BaseModel):
    items: list[TrashItem]
    total: int
    page: int
    page_size: int

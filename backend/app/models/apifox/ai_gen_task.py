"""Apifox AI 生成用例 · 任务模型（落库任务化，支持批量 + 刷新/重登可恢复）。

任务主表 apifox_ai_gen_tasks + 接口级子项 apifox_ai_gen_task_items。子项 result_cases
存生成的用例预览（CaseCreate JSON 列表，未入库），用户勾选后经 apply 才落用例表。
执行由后台 worker 驱动（独立于 HTTP 连接），故进度可恢复。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# 任务/子项状态机
TASK_STATUSES = ("pending", "running", "succeeded", "partial", "failed", "canceled")
ITEM_STATUSES = ("pending", "running", "succeeded", "failed", "canceled")


class ApifoxAiGenTask(Base):
    __tablename__ = "apifox_ai_gen_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # 任务是后台执行日志，与项目/接口松耦合：用普通索引列而非 FK，避免残留任务行阻塞删项目/删接口；
    # 项目硬删由 project_cleanup 批量清理，接口缺失时前端展示「接口已删除」。
    project_id: Mapped[int] = mapped_column(Integer, index=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    mode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # llm|mock，跑起来才定
    provider_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    categories: Mapped[str] = mapped_column(Text)  # JSON: [{"category","count"}]
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    done_items: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ApifoxAiGenTaskItem(Base):
    __tablename__ = "apifox_ai_gen_task_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("apifox_ai_gen_tasks.id"), index=True)
    endpoint_id: Mapped[int] = mapped_column(Integer, index=True)  # 松耦合：无 FK，容忍接口被删
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    generated_count: Mapped[int] = mapped_column(Integer, default=0)
    applied_count: Mapped[int] = mapped_column(Integer, default=0)
    result_cases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: CaseCreate[]
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

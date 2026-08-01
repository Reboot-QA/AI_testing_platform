"""Apifox 重构 · 运行记录（执行快照，反规范化落库供报告展示）。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApifoxRun(Base):
    __tablename__ = "apifox_runs"

    # 报告分页热路径复合索引：过滤 project_id + parent_run_id，按 chain_head_id 倒序走索引
    # （消除 ORDER BY COALESCE(...) 的 filesort，LIMIT 可提前终止）。见 run_repo._top_level_runs_query。
    __table_args__ = (
        Index("ix_apifox_runs_chain_page", "project_id", "parent_run_id", "chain_head_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    # 套件运行的父运行 id；套件子运行(各用例/场景)指向它，单跑为 NULL
    parent_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("apifox_runs.id"), nullable=True, index=True
    )
    # case | scenario | suite
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[int] = mapped_column(Integer)
    target_name: Mapped[str] = mapped_column(String(200), default="")
    environment_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # running | passed | failed
    status: Mapped[str] = mapped_column(String(20), default="running")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pass_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    triggered_by: Mapped[str] = mapped_column(String(100), default="manual")
    # 数据驱动/循环多轮运行的每组注入数据 JSON（[{...}, ...]，单轮运行为空），供报告按组展示
    iterations_meta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 定时任务失败自动重试链：retry_of_run_id 指向本链首次 run（首次自己为 NULL）；
    # attempt 为第几次尝试(1 基)。报告列表据此把同一次触发的多次尝试折叠成一行。
    retry_of_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("apifox_runs.id"), nullable=True, index=True
    )
    attempt: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    # 重试链链头 id（= COALESCE(retry_of_run_id, id)）；创建时填自身 id、mark_retry 时改填链头 id。
    # 物化成真实列以支持索引排序（MySQL 不允许生成列引用 AUTO_INCREMENT 的 id）。
    chain_head_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class ApifoxRunStep(Base):
    __tablename__ = "apifox_run_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("apifox_runs.id"), index=True)
    # case | wait
    step_type: Mapped[str] = mapped_column(String(20), default="case")
    # 步骤在场景树中的嵌套深度（顶层 0），供报告缩进展示
    depth: Mapped[int] = mapped_column(Integer, default=0)
    # 数据驱动/循环运行时步骤所属的轮次（0 基），供报告按组展示
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    # 内层循环(loop)步骤所属的循环轮次全局序号（0=不在循环内），供报告统计「循环数」
    loop_round: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    case_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    case_name: Mapped[str] = mapped_column(String(200), default="")
    method: Mapped[str] = mapped_column(String(10), default="")
    url: Mapped[str] = mapped_column(String(1000), default="")
    # passed | failed | skipped
    status: Mapped[str] = mapped_column(String(20), default="passed")
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_headers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_headers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assertion_results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extract_results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    script_logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 响应契约校验结果 JSON（{passed,message,errors} 或 null）
    contract_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 诊断告警 JSON 列表（如 Binary 孤儿文件、Content-Type 不匹配）；不影响 status
    warnings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


@event.listens_for(ApifoxRun, "after_insert")
def _fill_chain_head_id(mapper, connection, target) -> None:
    """填 chain_head_id = COALESCE(retry_of_run_id, id)：非重试自成一链(=自身 id)，
    建行即带 retry_of_run_id 的归入链头。覆盖所有创建路径（生产 _start_run + 测试直建），
    保证报告分页按 chain_head_id 排序/折叠时该列恒有值、走复合索引。
    （生产重试经 mark_retry 在创建后才置 retry_of_run_id，那里另行同步 chain_head_id。）
    """
    if target.chain_head_id is None:
        connection.execute(
            ApifoxRun.__table__.update()
            .where(ApifoxRun.__table__.c.id == target.id)
            .values(chain_head_id=target.retry_of_run_id or target.id)
        )

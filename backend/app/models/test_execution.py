from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ManualTestRun(Base):
    __tablename__ = "manual_test_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    build_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="waiting")
    executor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    pending_count: Mapped[int] = mapped_column(Integer, default=0)
    pass_rate: Mapped[float] = mapped_column(Float, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="manual_test_runs")
    executor: Mapped[Optional["User"]] = relationship("User")
    cases: Mapped[List["ManualTestRunCase"]] = relationship(
        "ManualTestRunCase", back_populates="run", cascade="all, delete-orphan"
    )


class ManualTestRunCase(Base):
    __tablename__ = "manual_test_run_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("manual_test_runs.id"), index=True)
    testcase_id: Mapped[int] = mapped_column(ForeignKey("testcases.id"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[str] = mapped_column(String(20), default="pending")
    actual_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["ManualTestRun"] = relationship("ManualTestRun", back_populates="cases")
    testcase: Mapped["TestCase"] = relationship("TestCase")
    executor: Mapped[Optional["User"]] = relationship("User", foreign_keys=[executed_by])


from app.models.project import Project  # noqa: E402
from app.models.testcase import TestCase  # noqa: E402
from app.models.user import User  # noqa: E402

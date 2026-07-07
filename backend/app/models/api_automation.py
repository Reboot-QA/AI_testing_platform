from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApiEnvironment(Base):
    __tablename__ = "api_environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    base_url: Mapped[str] = mapped_column(String(500))
    default_headers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    variables: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="api_environments")
    suites: Mapped[List["ApiTestSuite"]] = relationship("ApiTestSuite", back_populates="environment")


class ApiTestSuite(Base):
    __tablename__ = "api_test_suites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("api_test_suites.id"), nullable=True, index=True)
    is_folder: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    environment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("api_environments.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="api_test_suites")
    parent: Mapped[Optional["ApiTestSuite"]] = relationship(
        "ApiTestSuite", remote_side="ApiTestSuite.id", back_populates="children"
    )
    children: Mapped[List["ApiTestSuite"]] = relationship("ApiTestSuite", back_populates="parent")
    environment: Mapped[Optional["ApiEnvironment"]] = relationship("ApiEnvironment", back_populates="suites")
    cases: Mapped[List["ApiTestCase"]] = relationship(
        "ApiTestCase", back_populates="suite", cascade="all, delete-orphan"
    )
    runs: Mapped[List["ApiTestRun"]] = relationship(
        "ApiTestRun", back_populates="suite", cascade="all, delete-orphan"
    )
    scheduled_task_links: Mapped[List["ApiScheduledTaskSuite"]] = relationship(
        "ApiScheduledTaskSuite", back_populates="suite", cascade="all, delete-orphan"
    )


class ApiTestCase(Base):
    __tablename__ = "api_test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    suite_id: Mapped[int] = mapped_column(ForeignKey("api_test_suites.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    method: Mapped[str] = mapped_column(String(10), default="GET")
    path: Mapped[str] = mapped_column(String(500))
    headers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assertions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    suite: Mapped["ApiTestSuite"] = relationship("ApiTestSuite", back_populates="cases")


class ApiTestRun(Base):
    __tablename__ = "api_test_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    suite_id: Mapped[int] = mapped_column(ForeignKey("api_test_suites.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, default=0)
    pass_rate: Mapped[float] = mapped_column(Float, default=0)
    triggered_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    suite: Mapped["ApiTestSuite"] = relationship("ApiTestSuite", back_populates="runs")
    step_results: Mapped[List["ApiTestStepResult"]] = relationship(
        "ApiTestStepResult", back_populates="run", cascade="all, delete-orphan"
    )


class ApiTestStepResult(Base):
    __tablename__ = "api_test_step_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("api_test_runs.id"), index=True)
    case_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    case_name: Mapped[str] = mapped_column(String(200))
    method: Mapped[str] = mapped_column(String(10))
    url: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20))
    duration_ms: Mapped[float] = mapped_column(Float, default=0)
    request_headers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    request_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assertion_results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["ApiTestRun"] = relationship("ApiTestRun", back_populates="step_results")


class ApiScheduledTaskSuite(Base):
    __tablename__ = "api_scheduled_task_suites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("api_scheduled_tasks.id", ondelete="CASCADE"), index=True)
    suite_id: Mapped[int] = mapped_column(ForeignKey("api_test_suites.id", ondelete="CASCADE"), index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    task: Mapped["ApiScheduledTask"] = relationship("ApiScheduledTask", back_populates="task_suites")
    suite: Mapped["ApiTestSuite"] = relationship("ApiTestSuite", back_populates="scheduled_task_links")


class ApiScheduledTask(Base):
    __tablename__ = "api_scheduled_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    suite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("api_test_suites.id"), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    schedule_type: Mapped[str] = mapped_column(String(20), default="daily")
    run_time: Mapped[str] = mapped_column(String(5), default="09:00")
    week_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    interval_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_run_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    task_suites: Mapped[List["ApiScheduledTaskSuite"]] = relationship(
        "ApiScheduledTaskSuite", back_populates="task", cascade="all, delete-orphan"
    )


from app.models.project import Project  # noqa: E402

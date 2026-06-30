from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TestCase(Base):
    __tablename__ = "testcases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    requirement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("requirements.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    case_type: Mapped[str] = mapped_column(String(30), default="functional")
    priority: Mapped[str] = mapped_column(String(10), default="P1")
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_results: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    review_status: Mapped[str] = mapped_column(String(20), default="draft")
    ai_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="testcases")
    requirement: Mapped[Optional["Requirement"]] = relationship("Requirement", back_populates="testcases")


from app.models.project import Project  # noqa: E402
from app.models.requirement import Requirement  # noqa: E402

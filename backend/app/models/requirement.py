from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    req_type: Mapped[str] = mapped_column(String(30), default="functional")
    priority: Mapped[str] = mapped_column(String(10), default="P1")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    source: Mapped[str] = mapped_column(String(30), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="requirements")
    testcases: Mapped[List["TestCase"]] = relationship("TestCase", back_populates="requirement")


from app.models.project import Project  # noqa: E402
from app.models.testcase import TestCase  # noqa: E402

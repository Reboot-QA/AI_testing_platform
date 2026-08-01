"""AI 功能用例生成任务与 testcases 行的关联（供任务详情查看）。"""

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HubAiTaskCaseItem(Base):
    __tablename__ = "hub_ai_task_case_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(Integer, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    testcase_id: Mapped[int] = mapped_column(Integer, index=True)

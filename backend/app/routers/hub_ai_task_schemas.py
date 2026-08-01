from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class HubAiTaskRequirementItemOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    req_type: str = "functional"
    priority: str = "P1"
    requirement_id: Optional[int] = None
    imported_at: Optional[datetime] = None


class HubAiTaskRequirementDiscard(BaseModel):
    item_ids: List[int]


class HubAiTaskRequirementDiscardResponse(BaseModel):
    discarded: int
    message: str

class HubAiTaskRequirementsOut(BaseModel):
    items: List[HubAiTaskRequirementItemOut]
    total: int


class HubAiTaskCaseBrief(BaseModel):
    id: int
    link_id: int = 0
    title: str
    case_type: str
    priority: str
    preconditions: Optional[str] = None
    steps: Optional[str] = None
    expected_results: Optional[str] = None
    tags: Optional[str] = None
    requirement_title: str = ""
    review_status: str = ""


class HubAiTaskCasesOut(BaseModel):
    items: List[HubAiTaskCaseBrief]
    total: int


class HubAiTaskBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    task_type: str
    status: str
    target: str
    category_label: str
    model_label: str = ""
    total_items: int
    done_items: int
    generated_total: int
    applied_total: int
    error: Optional[str] = None
    creator_name: str = ""
    created_at: datetime
    finished_at: Optional[datetime] = None


class HubAiTaskPageOut(BaseModel):
    total: int
    items: List[HubAiTaskBrief]


class HubAiTaskOut(HubAiTaskBrief):
    meta: Optional[Dict[str, Any]] = None
    requirements: Optional[List[HubAiTaskRequirementItemOut]] = None

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: str = "tester"

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()
        if not value or not USERNAME_PATTERN.match(value):
            raise ValueError("用户名只能包含字母、数字和下划线，不能包含中文或特殊符号")
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool
    must_change_password: bool = False
    department_id: Optional[int] = None
    department_name: str = ""
    created_at: datetime
    menu_permissions: List[str] = []

    class Config:
        from_attributes = True


class UserCreateByAdmin(UserBase):
    password: str = Field(min_length=6)
    department_id: Optional[int] = None
    menu_permissions: Optional[List[str]] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    department_id: Optional[int] = None


class UserPasswordReset(BaseModel):
    password: str = Field(min_length=6)


class UserPasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


class MenuDefinitionOut(BaseModel):
    key: str
    label: str
    path: str
    group: str


class UserPermissionsOut(BaseModel):
    user_id: int
    username: str
    role: str
    menu_permissions: List[str]


class UserPermissionsUpdate(BaseModel):
    menu_permissions: List[str] = Field(default_factory=list)


class DepartmentPermissionsOut(BaseModel):
    department_id: int
    department_name: str
    menu_permissions: List[str]


class DepartmentPermissionsUpdate(BaseModel):
    menu_permissions: List[str] = Field(default_factory=list)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[int] = None  # 变更负责人：仅系统管理员可用（router 校验）


class ProjectOut(ProjectBase):
    id: int
    owner_id: int
    owner_name: str = ""
    department_id: Optional[int] = None
    department_name: str = ""
    status: str
    created_at: datetime
    requirement_count: int = 0
    testcase_count: int = 0

    class Config:
        from_attributes = True


class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DepartmentOut(DepartmentBase):
    id: int
    user_count: int = 0
    project_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RequirementBase(BaseModel):
    title: str
    description: Optional[str] = None
    req_type: str = "functional"
    priority: str = "P1"


class RequirementCreate(RequirementBase):
    project_id: int


class RequirementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    req_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


class RequirementOut(RequirementBase):
    id: int
    project_id: int
    project_name: str = ""
    status: str
    source: str
    created_by_id: Optional[int] = None
    creator_name: str = ""
    created_at: datetime
    testcase_count: int = 0

    class Config:
        from_attributes = True


class RequirementPageOut(BaseModel):
    items: List[RequirementOut]
    total: int
    page: int
    page_size: int


class RequirementBatchStatusUpdate(BaseModel):
    project_id: int
    requirement_ids: List[int] = Field(min_length=1)
    status: str


class RequirementBatchStatusResponse(BaseModel):
    updated_count: int
    message: str


class RequirementBatchDelete(BaseModel):
    project_id: int
    requirement_ids: List[int] = Field(min_length=1)


class RequirementBatchDeleteResponse(BaseModel):
    deleted_count: int
    skipped_count: int
    skipped_titles: List[str] = []
    message: str


class ExtractedRequirement(BaseModel):
    title: str
    description: Optional[str] = None
    req_type: str = "functional"
    priority: str = "P1"


class RequirementExtractResponse(BaseModel):
    filename: str
    requirements: List[ExtractedRequirement]
    mode: str
    provider_name: Optional[str] = None
    model: Optional[str] = None
    truncated: bool = False
    message: str = ""


class RequirementBatchImport(BaseModel):
    project_id: int
    requirements: List[ExtractedRequirement] = Field(min_length=1)


class RequirementBatchImportResponse(BaseModel):
    imported_count: int
    requirements: List[RequirementOut]
    message: str


class RequirementFileImportResponse(BaseModel):
    imported_count: int
    skipped_count: int = 0
    message: str


class TestCaseFileImportResponse(BaseModel):
    imported_count: int
    skipped_count: int = 0
    message: str


class TestCaseBase(BaseModel):
    title: str
    case_type: str = "functional"
    priority: str = "P1"
    preconditions: Optional[str] = None
    steps: Optional[str] = None
    expected_results: Optional[str] = None
    tags: Optional[str] = None
    requirement_id: Optional[int] = None


class TestCaseCreate(TestCaseBase):
    project_id: int


class TestCaseUpdate(BaseModel):
    title: Optional[str] = None
    case_type: Optional[str] = None
    priority: Optional[str] = None
    preconditions: Optional[str] = None
    steps: Optional[str] = None
    expected_results: Optional[str] = None
    tags: Optional[str] = None
    requirement_id: Optional[int] = None
    review_status: Optional[str] = None


class TestCaseOut(TestCaseBase):
    id: int
    project_id: int
    project_name: str = ""
    requirement_title: str = ""
    source: str
    review_status: str
    created_by_id: Optional[int] = None
    creator_name: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class TestCasePageOut(BaseModel):
    items: List[TestCaseOut]
    total: int
    page: int
    page_size: int


class AIGenerateRequest(BaseModel):
    project_id: int
    requirement_id: Optional[int] = None
    requirement_ids: Optional[List[int]] = None
    requirement_text: Optional[str] = None
    case_type: str = "functional"
    count: int = Field(default=5, ge=1, le=100)
    provider_id: Optional[int] = None


class AIGenerateResponse(BaseModel):
    generated_count: int
    testcases: List[TestCaseOut]
    mode: str
    provider_name: Optional[str] = None
    model: Optional[str] = None


class TestCaseBatchDelete(BaseModel):
    project_id: int
    case_ids: List[int] = Field(min_length=1)


class TestCaseBatchReviewUpdate(BaseModel):
    project_id: int
    case_ids: List[int] = Field(min_length=1)
    review_status: str


class TestCaseBatchReviewResponse(BaseModel):
    updated_count: int
    skipped_count: int
    message: str


class BatchDeleteResponse(BaseModel):
    deleted_count: int
    message: str


class DashboardStats(BaseModel):
    project_count: int
    requirement_count: int
    testcase_count: int
    ai_generated_count: int
    pending_review_count: int


class LLMSettingsOut(BaseModel):
    mock_mode: bool
    active_provider_id: Optional[int] = None
    providers: List["LLMProviderOut"] = []


class LLMProviderOut(BaseModel):
    id: int
    name: str
    api_base: str
    model: str
    enabled: bool
    is_default: bool
    api_key_configured: bool
    api_key_masked: str
    created_at: datetime

    class Config:
        from_attributes = True


class LLMProviderOptionOut(BaseModel):
    id: int
    name: str
    model: str
    is_default: bool
    api_key_configured: bool


class LLMGenerateOptionsOut(BaseModel):
    mock_mode: bool
    active_provider_id: Optional[int] = None
    providers: List[LLMProviderOptionOut] = []


class LLMProviderCreate(BaseModel):
    name: str
    api_base: str
    model: str
    api_key: Optional[str] = None
    enabled: bool = True
    is_default: bool = False


class LLMProviderUpdate(BaseModel):
    name: Optional[str] = None
    api_base: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None


class MockModeUpdate(BaseModel):
    mock_mode: bool


class LLMSettingsUpdate(BaseModel):
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    mock_mode: Optional[bool] = None


class LLMTestRequest(BaseModel):
    provider_id: Optional[int] = None
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    mock_mode: Optional[bool] = None


class LLMTestResponse(BaseModel):
    success: bool
    message: str


class ApiEnvironmentBase(BaseModel):
    name: str
    base_url: str
    default_headers: Optional[str] = None
    variables: Optional[str] = None
    description: Optional[str] = None


class ApiEnvironmentCreate(ApiEnvironmentBase):
    project_id: int


class ApiEnvironmentUpdate(BaseModel):
    name: Optional[str] = None
    base_url: Optional[str] = None
    default_headers: Optional[str] = None
    variables: Optional[str] = None
    description: Optional[str] = None


class ApiEnvironmentOut(ApiEnvironmentBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiGlobalVariablesOut(BaseModel):
    variables: Dict[str, str] = {}


class ApiGlobalVariablesUpdate(BaseModel):
    variables: Dict[str, str] = {}


class ApiTestSuiteBase(BaseModel):
    name: str
    description: Optional[str] = None
    environment_id: Optional[int] = None
    parent_id: Optional[int] = None
    is_folder: bool = False
    sort_order: int = 0


class ApiTestSuiteCreate(ApiTestSuiteBase):
    project_id: int


class ApiTestSuiteUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    environment_id: Optional[int] = None
    parent_id: Optional[int] = None
    is_folder: Optional[bool] = None
    sort_order: Optional[int] = None


class ApiTestSuiteOut(ApiTestSuiteBase):
    id: int
    project_id: int
    case_count: int = 0
    last_run_status: Optional[str] = None
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiTestCaseBase(BaseModel):
    name: str
    method: str = "GET"
    path: str
    headers: Optional[str] = None
    body: Optional[str] = None
    assertions: Optional[str] = None
    sort_order: int = 0
    enabled: bool = True


class ApiTestCaseCreate(ApiTestCaseBase):
    suite_id: int


class ApiTestCaseUpdate(BaseModel):
    name: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    headers: Optional[str] = None
    body: Optional[str] = None
    assertions: Optional[str] = None
    sort_order: Optional[int] = None
    enabled: Optional[bool] = None
    suite_id: Optional[int] = None


class ApiTestCaseCopyRequest(BaseModel):
    suite_id: Optional[int] = None


class ApiCaseBatchDeleteRequest(BaseModel):
    case_ids: List[int]


class ApiCaseBatchDeleteResponse(BaseModel):
    deleted_count: int
    message: str


class ApiRunBatchDeleteRequest(BaseModel):
    run_ids: List[int]


class ApiRunBatchDeleteResponse(BaseModel):
    deleted_count: int
    message: str


class ApiRunBatchExportRequest(BaseModel):
    run_ids: List[int]
    format: str = "excel"


class ApiTestCaseOut(ApiTestCaseBase):
    id: int
    suite_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiAssertionResultOut(BaseModel):
    type: str
    passed: bool
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    message: str = ""
    scope: Optional[str] = None
    source: Optional[str] = None


class ApiTestStepResultOut(BaseModel):
    id: int
    case_id: Optional[int] = None
    case_name: str
    method: str
    url: str
    status: str
    duration_ms: float
    request_headers: Optional[str] = None
    request_body: Optional[str] = None
    response_status: Optional[int] = None
    response_headers: Optional[str] = None
    response_body: Optional[str] = None
    assertion_results: List[ApiAssertionResultOut] = []
    error_message: Optional[str] = None
    created_at: datetime


class ApiTestRunSummaryOut(BaseModel):
    id: int
    suite_id: int
    suite_name: str = ""
    status: str
    total_count: int
    passed_count: int
    failed_count: int
    skipped_count: int
    duration_ms: float
    pass_rate: float
    triggered_by: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class ApiTestRunPageOut(BaseModel):
    items: List[ApiTestRunSummaryOut]
    total: int
    page: int
    page_size: int


class ApiTestRunDetailOut(ApiTestRunSummaryOut):
    step_results: List[ApiTestStepResultOut] = []
    run_ids: List[int] = Field(default_factory=list)
    suite_sections: List["ApiTestRunSuiteSectionOut"] = Field(default_factory=list)


class ApiTestRunSuiteSectionOut(BaseModel):
    run_id: int
    suite_id: int
    suite_name: str = ""
    status: str
    total_count: int
    passed_count: int
    failed_count: int
    duration_ms: float
    pass_rate: float
    step_results: List[ApiTestStepResultOut] = []


class ApiRunTriggerOut(BaseModel):
    run_id: int
    run_ids: List[int] = Field(default_factory=list)
    message: str


class ApiCaseDebugRequest(BaseModel):
    environment_id: int
    method: str = "GET"
    path: str
    headers: Optional[str] = None
    body: Optional[str] = None
    assertions: Optional[str] = None
    data_drive_index: Optional[int] = None
    run_all_data_sets: bool = False


class ApiDataParamItem(BaseModel):
    key: str = ""
    value: str = ""
    enabled: bool = True


class ApiDataGenerateRequest(BaseModel):
    name: Optional[str] = None
    method: str = "GET"
    path: str = ""
    url: Optional[str] = None
    body: Optional[str] = None
    body_type: str = "json"
    headers: Optional[str] = None
    query_params: List[ApiDataParamItem] = Field(default_factory=list)
    path_params: List[ApiDataParamItem] = Field(default_factory=list)
    provider_id: Optional[int] = None


class ApiDataGenerateOut(BaseModel):
    body: Optional[str] = None
    query: List[ApiDataParamItem] = Field(default_factory=list)
    path: List[ApiDataParamItem] = Field(default_factory=list)
    mode: str = "mock"
    message: str = ""


class ApiDataBatchGenerateRequest(BaseModel):
    case_ids: List[int] = Field(default_factory=list)
    provider_id: Optional[int] = None


class ApiDataBatchGenerateItemOut(BaseModel):
    case_id: int
    case_name: str
    success: bool
    message: str = ""
    log: str = ""


class ApiDataBatchGenerateOut(BaseModel):
    updated_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    items: List[ApiDataBatchGenerateItemOut] = Field(default_factory=list)
    mode: str = "mock"
    message: str = ""


class ApiPreScriptDebugRequest(BaseModel):
    script: str = ""
    language: str = "javascript"
    variables: Dict[str, str] = Field(default_factory=dict)


class ApiPostScriptDebugRequest(BaseModel):
    script: str = ""
    language: str = "javascript"
    variables: Dict[str, str] = Field(default_factory=dict)
    response_body: str = ""
    response_status: Optional[int] = None
    response_headers: Dict[str, str] = Field(default_factory=dict)


class ApiPreScriptDebugOut(BaseModel):
    status: str
    logs: List[str] = Field(default_factory=list)
    variables: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ApiCaseDebugIterationOut(BaseModel):
    label: str
    status: str
    duration_ms: float
    request_method: str
    request_url: str
    request_headers: Optional[str] = None
    request_body: Optional[str] = None
    response_status: Optional[int] = None
    response_headers: Optional[str] = None
    response_body: Optional[str] = None
    assertion_results: List["ApiAssertionResultOut"] = Field(default_factory=list)
    error_message: Optional[str] = None
    request_message: str = ""
    extracted_variables: Dict[str, str] = Field(default_factory=dict)
    pre_script_logs: List[str] = Field(default_factory=list)


class ApiCaseDebugOut(BaseModel):
    status: str
    duration_ms: float
    request_method: str
    request_url: str
    request_headers: Optional[str] = None
    request_body: Optional[str] = None
    response_status: Optional[int] = None
    response_headers: Optional[str] = None
    response_body: Optional[str] = None
    assertion_results: List[ApiAssertionResultOut] = Field(default_factory=list)
    error_message: Optional[str] = None
    request_message: str = ""
    extracted_variables: Dict[str, str] = Field(default_factory=dict)
    pre_script_logs: List[str] = Field(default_factory=list)
    iterations: List[ApiCaseDebugIterationOut] = Field(default_factory=list)


class CaptureImportRequest(BaseModel):
    suite_id: int
    raw_text: str
    case_name: Optional[str] = None
    auto_environment: bool = True
    preview: bool = False


class CaptureParsedItemOut(BaseModel):
    name: str
    method: str
    path: str
    base_url: str
    full_url: str
    headers: str = ""
    body: str = ""
    input_params: str = ""
    query_params: List[ApiDataParamItem] = Field(default_factory=list)
    path_params: List[ApiDataParamItem] = Field(default_factory=list)
    assertions: str = ""
    source: str = "fetch"


class CaptureImportOut(BaseModel):
    preview: bool = False
    imported_count: int = 0
    environment_id: Optional[int] = None
    case_ids: List[int] = Field(default_factory=list)
    items: List[CaptureParsedItemOut] = Field(default_factory=list)
    message: str = ""


class SwaggerImportRequest(BaseModel):
    suite_id: int
    source_type: str = "content"
    raw_text: Optional[str] = None
    swagger_url: Optional[str] = None
    base_url: Optional[str] = None
    auto_environment: bool = True
    preview: bool = False
    items: Optional[List[CaptureParsedItemOut]] = None


class SwaggerPreviewGenerateRequest(BaseModel):
    items: List[CaptureParsedItemOut] = Field(default_factory=list)
    provider_id: Optional[int] = None


class SwaggerPreviewGenerateItemOut(BaseModel):
    name: str
    method: str = ""
    success: bool = False
    skipped: bool = False
    message: str = ""
    log: str = ""


class SwaggerPreviewGenerateOut(BaseModel):
    items: List[CaptureParsedItemOut] = Field(default_factory=list)
    details: List[SwaggerPreviewGenerateItemOut] = Field(default_factory=list)
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    fallback_count: int = 0
    mode: str = "mock"
    message: str = ""


class SwaggerImportOut(BaseModel):
    preview: bool = False
    imported_count: int = 0
    environment_id: Optional[int] = None
    case_ids: List[int] = Field(default_factory=list)
    items: List[CaptureParsedItemOut] = Field(default_factory=list)
    message: str = ""


class ApiScheduledTaskBase(BaseModel):
    name: str
    suite_ids: List[int] = Field(..., min_length=1)
    schedule_type: str = "daily"
    run_time: str = "09:00"
    week_day: Optional[int] = None
    interval_minutes: Optional[int] = None
    enabled: bool = True


class ApiScheduledTaskCreate(ApiScheduledTaskBase):
    project_id: int


class ApiScheduledTaskUpdate(BaseModel):
    name: Optional[str] = None
    suite_ids: Optional[List[int]] = None
    schedule_type: Optional[str] = None
    run_time: Optional[str] = None
    week_day: Optional[int] = None
    interval_minutes: Optional[int] = None
    enabled: Optional[bool] = None


class ApiScheduledTaskOut(ApiScheduledTaskBase):
    id: int
    project_id: int
    suite_id: Optional[int] = None
    suite_name: str = ""
    suite_names: List[str] = Field(default_factory=list)
    schedule_desc: str = ""
    last_run_at: Optional[datetime] = None
    last_run_id: Optional[int] = None
    last_run_ids: List[int] = Field(default_factory=list)
    last_run_status: Optional[str] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


EXECUTION_RESULTS = {"pending", "pass", "fail", "blocked", "skip"}
EXECUTION_RUN_STATUSES = {"waiting", "running", "finished"}


class ManualTestRunCreate(BaseModel):
    project_id: int
    name: str
    build_name: Optional[str] = None
    description: Optional[str] = None
    case_ids: List[int] = Field(min_length=1)
    requirement_id: Optional[int] = None
    requirement_ids: Optional[List[int]] = None


class ManualTestRunUpdate(BaseModel):
    name: Optional[str] = None
    build_name: Optional[str] = None
    description: Optional[str] = None


class ManualTestRunCaseResultUpdate(BaseModel):
    result: str
    actual_result: Optional[str] = None
    remark: Optional[str] = None


class ManualTestRunCaseOut(BaseModel):
    id: int
    run_id: int
    testcase_id: int
    sort_order: int
    result: str
    actual_result: Optional[str] = None
    remark: Optional[str] = None
    executed_by: Optional[int] = None
    executor_name: str = ""
    executed_at: Optional[datetime] = None
    case_title: str = ""
    case_priority: str = ""
    case_type: str = ""
    preconditions: Optional[str] = None
    steps: Optional[str] = None
    expected_results: Optional[str] = None
    requirement_id: Optional[int] = None

    class Config:
        from_attributes = True


class ManualTestRunSummaryOut(BaseModel):
    id: int
    project_id: int
    name: str
    build_name: Optional[str] = None
    description: Optional[str] = None
    status: str
    executor_id: Optional[int] = None
    executor_name: str = ""
    total_count: int
    passed_count: int
    failed_count: int
    blocked_count: int
    skipped_count: int
    pending_count: int
    pass_rate: float
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ManualTestRunDetailOut(ManualTestRunSummaryOut):
    cases: List[ManualTestRunCaseOut] = Field(default_factory=list)

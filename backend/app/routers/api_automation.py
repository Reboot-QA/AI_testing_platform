import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.api_automation import (
    ApiEnvironment,
    ApiScheduledTask,
    ApiTestCase,
    ApiTestRun,
    ApiTestStepResult,
    ApiTestSuite,
)
from app.models.project import Project
from app.models.user import User
from app.schemas import (
    ApiAssertionResultOut,
    ApiPreScriptDebugOut,
    ApiPreScriptDebugRequest,
    ApiPostScriptDebugRequest,
    ApiCaseDebugIterationOut,
    ApiCaseDebugOut,
    ApiCaseDebugRequest,
    ApiEnvironmentCreate,
    ApiEnvironmentOut,
    ApiEnvironmentUpdate,
    ApiRunTriggerOut,
    ApiTestCaseCreate,
    ApiTestCaseCopyRequest,
    ApiCaseBatchDeleteRequest,
    ApiCaseBatchDeleteResponse,
    ApiTestCaseOut,
    ApiTestCaseUpdate,
    ApiTestRunDetailOut,
    ApiTestRunSummaryOut,
    ApiTestStepResultOut,
    ApiTestSuiteCreate,
    ApiTestSuiteOut,
    ApiTestSuiteUpdate,
    CaptureImportOut,
    CaptureImportRequest,
    CaptureParsedItemOut,
    ApiScheduledTaskCreate,
    ApiScheduledTaskOut,
    ApiScheduledTaskUpdate,
)
from app.services.api_capture_service import parse_capture_text, parse_multiple_captures
from app.services.api_script_runner import run_post_script, run_pre_script
from app.services.api_request_builder import extract_meta_from_headers, iter_data_drive_variable_sets, prepare_case_request
from app.services.api_runner_service import run_api_suite, _execute_case, _dumps_json
from app.services.schedule_service import (
    execute_scheduled_task,
    format_schedule_desc,
    refresh_task_schedule,
    validate_schedule_fields,
)

router = APIRouter(prefix="/api-automation", tags=["接口自动化"])


def _get_owned_project(db: Session, project_id: int, user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _get_owned_suite(db: Session, suite_id: int, user: User) -> ApiTestSuite:
    suite = (
        db.query(ApiTestSuite)
        .join(Project, Project.id == ApiTestSuite.project_id)
        .filter(ApiTestSuite.id == suite_id, Project.owner_id == user.id)
        .first()
    )
    if not suite:
        raise HTTPException(status_code=404, detail="测试套件不存在")
    return suite


def _get_owned_executable_suite(db: Session, suite_id: int, user: User) -> ApiTestSuite:
    suite = _get_owned_suite(db, suite_id, user)
    if suite.is_folder:
        raise HTTPException(status_code=400, detail="目录不能执行或管理用例")
    return suite


def _validate_suite_parent(
    db: Session,
    project_id: int,
    parent_id: Optional[int],
    *,
    exclude_id: Optional[int] = None,
) -> None:
    if parent_id is None:
        return
    parent = (
        db.query(ApiTestSuite)
        .filter(ApiTestSuite.id == parent_id, ApiTestSuite.project_id == project_id)
        .first()
    )
    if not parent:
        raise HTTPException(status_code=400, detail="父目录不存在或不属于当前项目")
    if not parent.is_folder:
        raise HTTPException(status_code=400, detail="父节点必须是目录")
    if exclude_id is not None and parent_id == exclude_id:
        raise HTTPException(status_code=400, detail="不能移动到自身目录下")

    current_id = parent.parent_id
    while current_id:
        if current_id == exclude_id:
            raise HTTPException(status_code=400, detail="不能移动到自身或子目录下")
        node = db.query(ApiTestSuite).filter(ApiTestSuite.id == current_id).first()
        current_id = node.parent_id if node else None


def _validate_suite_payload(
    db: Session,
    *,
    project_id: int,
    is_folder: bool,
    environment_id: Optional[int],
    parent_id: Optional[int],
    exclude_id: Optional[int] = None,
) -> None:
    _validate_suite_parent(db, project_id, parent_id, exclude_id=exclude_id)
    if is_folder and environment_id:
        raise HTTPException(status_code=400, detail="目录不能绑定执行环境")
    if not is_folder and not environment_id:
        raise HTTPException(status_code=400, detail="测试套件必须选择执行环境")


def _suite_has_children(db: Session, suite_id: int) -> bool:
    return (
        db.query(ApiTestSuite.id)
        .filter(ApiTestSuite.parent_id == suite_id)
        .first()
        is not None
    )


def _unique_copy_name(db: Session, model, filters: Dict[str, Any], base_name: str) -> str:
    candidate = f"{base_name} 副本"
    suffix = 2
    while db.query(model.id).filter_by(**filters, name=candidate).first():
        candidate = f"{base_name} 副本{suffix}"
        suffix += 1
    return candidate


def _copy_case_record(db: Session, case: ApiTestCase, target_suite_id: int, name: Optional[str] = None) -> ApiTestCase:
    max_order = (
        db.query(func.max(ApiTestCase.sort_order))
        .filter(ApiTestCase.suite_id == target_suite_id)
        .scalar()
    ) or 0
    new_case = ApiTestCase(
        suite_id=target_suite_id,
        name=name or _unique_copy_name(db, ApiTestCase, {"suite_id": target_suite_id}, case.name),
        method=case.method,
        path=case.path,
        headers=case.headers,
        body=case.body,
        assertions=case.assertions,
        sort_order=max_order + 1,
        enabled=case.enabled,
    )
    db.add(new_case)
    return new_case


def _copy_suite_record(
    db: Session,
    source: ApiTestSuite,
    *,
    parent_id: Optional[int],
    name: Optional[str] = None,
) -> ApiTestSuite:
    new_suite = ApiTestSuite(
        project_id=source.project_id,
        parent_id=parent_id,
        is_folder=source.is_folder,
        sort_order=source.sort_order,
        environment_id=source.environment_id,
        name=name
        or _unique_copy_name(
            db,
            ApiTestSuite,
            {"project_id": source.project_id, "parent_id": parent_id},
            source.name,
        ),
        description=source.description,
    )
    db.add(new_suite)
    db.flush()

    if source.is_folder:
        children = (
            db.query(ApiTestSuite)
            .filter(ApiTestSuite.parent_id == source.id)
            .order_by(ApiTestSuite.is_folder.desc(), ApiTestSuite.sort_order.asc(), ApiTestSuite.id.asc())
            .all()
        )
        for child in children:
            _copy_suite_record(db, child, parent_id=new_suite.id, name=child.name)
    else:
        cases = (
            db.query(ApiTestCase)
            .filter(ApiTestCase.suite_id == source.id)
            .order_by(ApiTestCase.sort_order.asc(), ApiTestCase.id.asc())
            .all()
        )
        for case in cases:
            _copy_case_record(db, case, new_suite.id, name=case.name)
    return new_suite


def _get_owned_case(db: Session, case_id: int, user: User) -> ApiTestCase:
    case = (
        db.query(ApiTestCase)
        .join(ApiTestSuite, ApiTestSuite.id == ApiTestCase.suite_id)
        .join(Project, Project.id == ApiTestSuite.project_id)
        .filter(ApiTestCase.id == case_id, Project.owner_id == user.id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="接口用例不存在")
    return case


def _parse_assertion_results(text: Optional[str]) -> List[ApiAssertionResultOut]:
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [ApiAssertionResultOut(**item) for item in data if isinstance(item, dict)]


def _suite_out(db: Session, suite: ApiTestSuite) -> ApiTestSuiteOut:
    case_count = db.query(ApiTestCase).filter(ApiTestCase.suite_id == suite.id).count()
    last_run = (
        db.query(ApiTestRun)
        .filter(ApiTestRun.suite_id == suite.id)
        .order_by(ApiTestRun.id.desc())
        .first()
    )
    return ApiTestSuiteOut(
        id=suite.id,
        project_id=suite.project_id,
        parent_id=suite.parent_id,
        is_folder=suite.is_folder,
        sort_order=suite.sort_order,
        name=suite.name,
        description=suite.description,
        environment_id=suite.environment_id,
        case_count=case_count,
        last_run_status=last_run.status if last_run else None,
        last_run_at=last_run.started_at if last_run else None,
        created_at=suite.created_at,
        updated_at=suite.updated_at,
    )


def _run_summary_out(db: Session, run: ApiTestRun) -> ApiTestRunSummaryOut:
    suite = db.query(ApiTestSuite).filter(ApiTestSuite.id == run.suite_id).first()
    return ApiTestRunSummaryOut(
        id=run.id,
        suite_id=run.suite_id,
        suite_name=suite.name if suite else "",
        status=run.status,
        total_count=run.total_count,
        passed_count=run.passed_count,
        failed_count=run.failed_count,
        skipped_count=run.skipped_count,
        duration_ms=run.duration_ms,
        pass_rate=run.pass_rate,
        triggered_by=run.triggered_by,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _get_owned_schedule(db: Session, task_id: int, user: User) -> ApiScheduledTask:
    task = (
        db.query(ApiScheduledTask)
        .join(Project, Project.id == ApiScheduledTask.project_id)
        .filter(ApiScheduledTask.id == task_id, Project.owner_id == user.id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    return task


def _schedule_out(db: Session, task: ApiScheduledTask) -> ApiScheduledTaskOut:
    suite = db.query(ApiTestSuite).filter(ApiTestSuite.id == task.suite_id).first()
    return ApiScheduledTaskOut(
        id=task.id,
        project_id=task.project_id,
        suite_id=task.suite_id,
        suite_name=suite.name if suite else "",
        name=task.name,
        schedule_type=task.schedule_type,
        schedule_desc=format_schedule_desc(task),
        run_time=task.run_time,
        week_day=task.week_day,
        interval_minutes=task.interval_minutes,
        enabled=task.enabled,
        last_run_at=task.last_run_at,
        last_run_id=task.last_run_id,
        last_run_status=task.last_run_status,
        next_run_at=task.next_run_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _run_detail_out(db: Session, run: ApiTestRun) -> ApiTestRunDetailOut:
    summary = _run_summary_out(db, run)
    steps = (
        db.query(ApiTestStepResult)
        .filter(ApiTestStepResult.run_id == run.id)
        .order_by(ApiTestStepResult.id.asc())
        .all()
    )
    step_results = [
        ApiTestStepResultOut(
            id=step.id,
            case_id=step.case_id,
            case_name=step.case_name,
            method=step.method,
            url=step.url,
            status=step.status,
            duration_ms=step.duration_ms,
            request_headers=step.request_headers,
            request_body=step.request_body,
            response_status=step.response_status,
            response_headers=step.response_headers,
            response_body=step.response_body,
            assertion_results=_parse_assertion_results(step.assertion_results),
            error_message=step.error_message,
            created_at=step.created_at,
        )
        for step in steps
    ]
    return ApiTestRunDetailOut(**summary.model_dump(), step_results=step_results)


@router.get("/environments", response_model=List[ApiEnvironmentOut])
def list_environments(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user)
    return (
        db.query(ApiEnvironment)
        .filter(ApiEnvironment.project_id == project_id)
        .order_by(ApiEnvironment.id.desc())
        .all()
    )


@router.post("/environments", response_model=ApiEnvironmentOut)
def create_environment(
    data: ApiEnvironmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, data.project_id, current_user)
    env = ApiEnvironment(**data.model_dump())
    db.add(env)
    db.commit()
    db.refresh(env)
    return env


@router.put("/environments/{env_id}", response_model=ApiEnvironmentOut)
def update_environment(
    env_id: int,
    data: ApiEnvironmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    env = (
        db.query(ApiEnvironment)
        .join(Project, Project.id == ApiEnvironment.project_id)
        .filter(ApiEnvironment.id == env_id, Project.owner_id == current_user.id)
        .first()
    )
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(env, key, value)
    db.commit()
    db.refresh(env)
    return env


@router.delete("/environments/{env_id}")
def delete_environment(
    env_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    env = (
        db.query(ApiEnvironment)
        .join(Project, Project.id == ApiEnvironment.project_id)
        .filter(ApiEnvironment.id == env_id, Project.owner_id == current_user.id)
        .first()
    )
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    db.delete(env)
    db.commit()
    return {"message": "删除成功"}


@router.get("/suites", response_model=List[ApiTestSuiteOut])
def list_suites(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user)
    suites = (
        db.query(ApiTestSuite)
        .filter(ApiTestSuite.project_id == project_id)
        .order_by(ApiTestSuite.is_folder.desc(), ApiTestSuite.sort_order.asc(), ApiTestSuite.id.asc())
        .all()
    )
    return [_suite_out(db, suite) for suite in suites]


@router.post("/suites", response_model=ApiTestSuiteOut)
def create_suite(
    data: ApiTestSuiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, data.project_id, current_user)
    _validate_suite_payload(
        db,
        project_id=data.project_id,
        is_folder=data.is_folder,
        environment_id=data.environment_id,
        parent_id=data.parent_id,
    )
    if data.environment_id:
        env = (
            db.query(ApiEnvironment)
            .filter(ApiEnvironment.id == data.environment_id, ApiEnvironment.project_id == data.project_id)
            .first()
        )
        if not env:
            raise HTTPException(status_code=400, detail="环境不存在或不属于当前项目")
    payload = data.model_dump()
    if data.is_folder:
        payload["environment_id"] = None
    suite = ApiTestSuite(**payload)
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return _suite_out(db, suite)


@router.put("/suites/{suite_id}", response_model=ApiTestSuiteOut)
def update_suite(
    suite_id: int,
    data: ApiTestSuiteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suite = _get_owned_suite(db, suite_id, current_user)
    updates = data.model_dump(exclude_unset=True)
    next_is_folder = updates.get("is_folder", suite.is_folder)
    next_parent_id = updates.get("parent_id", suite.parent_id)
    next_environment_id = updates.get("environment_id", suite.environment_id)

    if next_is_folder:
        case_count = db.query(ApiTestCase).filter(ApiTestCase.suite_id == suite.id).count()
        if case_count:
            raise HTTPException(status_code=400, detail="套件下已有用例，不能改为目录")
        next_environment_id = None
        updates["environment_id"] = None

    _validate_suite_payload(
        db,
        project_id=suite.project_id,
        is_folder=next_is_folder,
        environment_id=next_environment_id,
        parent_id=next_parent_id,
        exclude_id=suite.id,
    )

    if next_environment_id:
        env = (
            db.query(ApiEnvironment)
            .filter(ApiEnvironment.id == next_environment_id, ApiEnvironment.project_id == suite.project_id)
            .first()
        )
        if not env:
            raise HTTPException(status_code=400, detail="环境不存在或不属于当前项目")
    for key, value in updates.items():
        setattr(suite, key, value)
    db.commit()
    db.refresh(suite)
    return _suite_out(db, suite)


@router.delete("/suites/{suite_id}")
def delete_suite(
    suite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suite = _get_owned_suite(db, suite_id, current_user)
    if suite.is_folder and _suite_has_children(db, suite.id):
        raise HTTPException(status_code=400, detail="目录非空，请先删除或移出子项")
    db.delete(suite)
    db.commit()
    return {"message": "删除成功"}


@router.post("/suites/{suite_id}/copy", response_model=ApiTestSuiteOut)
def copy_suite(
    suite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source = _get_owned_suite(db, suite_id, current_user)
    copied = _copy_suite_record(db, source, parent_id=source.parent_id)
    db.commit()
    db.refresh(copied)
    return _suite_out(db, copied)


@router.get("/cases", response_model=List[ApiTestCaseOut])
def list_cases(
    suite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_executable_suite(db, suite_id, current_user)
    return (
        db.query(ApiTestCase)
        .filter(ApiTestCase.suite_id == suite_id)
        .order_by(ApiTestCase.sort_order.asc(), ApiTestCase.id.asc())
        .all()
    )


@router.post("/cases", response_model=ApiTestCaseOut)
def create_case(
    data: ApiTestCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_executable_suite(db, data.suite_id, current_user)
    case = ApiTestCase(**data.model_dump())
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.put("/cases/{case_id}", response_model=ApiTestCaseOut)
def update_case(
    case_id: int,
    data: ApiTestCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)
    source_suite = _get_owned_suite(db, case.suite_id, current_user)
    updates = data.model_dump(exclude_unset=True)
    if "suite_id" in updates and updates["suite_id"] != case.suite_id:
        target_suite = _get_owned_executable_suite(db, updates["suite_id"], current_user)
        if target_suite.project_id != source_suite.project_id:
            raise HTTPException(status_code=400, detail="目标套件与当前项目不匹配")
    for key, value in updates.items():
        setattr(case, key, value)
    db.commit()
    db.refresh(case)
    return case


@router.post("/cases/{case_id}/copy", response_model=ApiTestCaseOut)
def copy_case(
    case_id: int,
    data: ApiTestCaseCopyRequest = Body(default_factory=ApiTestCaseCopyRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)
    target_suite_id = data.suite_id or case.suite_id
    if target_suite_id != case.suite_id:
        target_suite = _get_owned_executable_suite(db, target_suite_id, current_user)
        source_suite = _get_owned_suite(db, case.suite_id, current_user)
        if target_suite.project_id != source_suite.project_id:
            raise HTTPException(status_code=400, detail="目标套件与当前项目不匹配")
    copied = _copy_case_record(db, case, target_suite_id)
    db.commit()
    db.refresh(copied)
    return copied


@router.post("/cases/batch/delete", response_model=ApiCaseBatchDeleteResponse)
def batch_delete_cases(
    data: ApiCaseBatchDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not data.case_ids:
        raise HTTPException(status_code=400, detail="请选择要删除的用例")
    unique_ids = list(dict.fromkeys(data.case_ids))
    cases = (
        db.query(ApiTestCase)
        .join(ApiTestSuite, ApiTestSuite.id == ApiTestCase.suite_id)
        .join(Project, Project.id == ApiTestSuite.project_id)
        .filter(ApiTestCase.id.in_(unique_ids), Project.owner_id == current_user.id)
        .all()
    )
    if not cases:
        raise HTTPException(status_code=404, detail="未找到可删除的用例")
    for case in cases:
        db.delete(case)
    db.commit()
    deleted_count = len(cases)
    return ApiCaseBatchDeleteResponse(
        deleted_count=deleted_count,
        message=f"成功删除 {deleted_count} 条用例",
    )


@router.delete("/cases/{case_id}")
def delete_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = _get_owned_case(db, case_id, current_user)
    db.delete(case)
    db.commit()
    return {"message": "删除成功"}


def _format_form_body(form_data: Dict[str, Any]) -> str:
    if not form_data:
        return ""
    return "\n".join(f"{key}={value}" for key, value in form_data.items())


def _format_request_message(
    method: str,
    url: str,
    headers: dict,
    body: str,
    form_data: Optional[Dict[str, Any]] = None,
) -> str:
    lines = [f"Request Method: {method.upper()}", f"Request Url: {url}", "Request Headers:"]
    for key, value in (headers or {}).items():
        lines.append(f"{key}: {value}")
    if form_data:
        lines.extend(["", "Request Body (form-data):", _format_form_body(form_data)])
    elif body:
        lines.extend(["", "Request Body:", body])
    return "\n".join(lines)


@router.post("/scripts/pre/debug", response_model=ApiPreScriptDebugOut)
def debug_pre_script(
    data: ApiPreScriptDebugRequest,
    current_user: User = Depends(get_current_user),
):
    if not data.script or not data.script.strip():
        raise HTTPException(status_code=400, detail="预执行脚本不能为空")

    updated_variables, logs, error = run_pre_script(
        data.script,
        data.language,
        data.variables or {},
    )
    if error:
        return ApiPreScriptDebugOut(
            status="failed",
            logs=logs,
            variables=updated_variables,
            error_message=error,
        )
    return ApiPreScriptDebugOut(
        status="passed",
        logs=logs,
        variables=updated_variables,
        error_message=None,
    )


@router.post("/scripts/post/debug", response_model=ApiPreScriptDebugOut)
def debug_post_script(
    data: ApiPostScriptDebugRequest,
    current_user: User = Depends(get_current_user),
):
    if not data.script or not data.script.strip():
        raise HTTPException(status_code=400, detail="后置脚本不能为空")

    updated_variables, logs, error = run_post_script(
        data.script,
        data.language,
        data.variables or {},
        data.response_body,
        data.response_status,
        data.response_headers or {},
    )
    if error:
        return ApiPreScriptDebugOut(
            status="failed",
            logs=logs,
            variables=updated_variables,
            error_message=error,
        )
    return ApiPreScriptDebugOut(
        status="passed",
        logs=logs,
        variables=updated_variables,
        error_message=None,
    )


@router.post("/cases/debug", response_model=ApiCaseDebugOut)
def debug_case(
    data: ApiCaseDebugRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    environment = (
        db.query(ApiEnvironment)
        .join(Project, Project.id == ApiEnvironment.project_id)
        .filter(ApiEnvironment.id == data.environment_id, Project.owner_id == current_user.id)
        .first()
    )
    if not environment:
        raise HTTPException(status_code=404, detail="环境不存在")

    temp_case = ApiTestCase(
        suite_id=0,
        name="debug",
        method=data.method,
        path=data.path,
        headers=data.headers,
        body=data.body,
        assertions=data.assertions,
    )

    meta = extract_meta_from_headers(data.headers)
    variable_sets = iter_data_drive_variable_sets(meta)

    if data.run_all_data_sets and len(variable_sets) > 1:
        selected_sets = variable_sets
    elif data.data_drive_index is not None and 0 <= data.data_drive_index < len(variable_sets):
        selected_sets = [variable_sets[data.data_drive_index]]
    else:
        selected_sets = [variable_sets[0]]

    def build_debug_out(label: str, status: str, detail: Dict[str, Any]) -> ApiCaseDebugIterationOut:
        req = detail["request"]
        return ApiCaseDebugIterationOut(
            label=label,
            status=status,
            duration_ms=detail["duration_ms"],
            request_method=req["method"],
            request_url=req["url"],
            request_headers=_dumps_json(req["headers"]),
            request_body=req.get("body") or "",
            response_status=detail.get("response_status"),
            response_headers=_dumps_json(detail.get("response_headers") or {}),
            response_body=detail.get("response_body") or "",
            assertion_results=[ApiAssertionResultOut(**item) for item in detail.get("assertion_results") or []],
            error_message=detail.get("error_message"),
            request_message=_format_request_message(
                req["method"],
                req["url"],
                req["headers"],
                req.get("body") or "",
                req.get("form_data"),
            ),
            extracted_variables=detail.get("extracted_variables") or {},
            pre_script_logs=detail.get("pre_script_logs") or [],
        )

    iteration_results: List[ApiCaseDebugIterationOut] = []
    total_duration = 0.0
    overall_status = "passed"
    runtime_variables: Dict[str, str] = {}

    for label, variables in selected_sets:
        merged_variables = {**runtime_variables, **variables}
        status, detail = _execute_case(temp_case, environment, variables=merged_variables)
        runtime_variables.update(detail.get("extracted_variables") or {})
        total_duration += detail["duration_ms"]
        if status != "passed":
            overall_status = "failed"
        iteration_results.append(build_debug_out(label, status, detail))

    primary = iteration_results[0]
    return ApiCaseDebugOut(
        status=overall_status if len(iteration_results) > 1 else primary.status,
        duration_ms=total_duration if len(iteration_results) > 1 else primary.duration_ms,
        request_method=primary.request_method,
        request_url=primary.request_url,
        request_headers=primary.request_headers,
        request_body=primary.request_body,
        response_status=primary.response_status,
        response_headers=primary.response_headers,
        response_body=primary.response_body,
        assertion_results=primary.assertion_results,
        error_message=primary.error_message,
        request_message=primary.request_message,
        extracted_variables=primary.extracted_variables,
        pre_script_logs=primary.pre_script_logs,
        iterations=iteration_results if len(iteration_results) > 1 else [],
    )


@router.post("/suites/{suite_id}/run", response_model=ApiRunTriggerOut)
def run_suite(
    suite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suite = _get_owned_executable_suite(db, suite_id, current_user)
    try:
        run = run_api_suite(db, suite, triggered_by=current_user.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiRunTriggerOut(run_id=run.id, message="执行完成")


@router.get("/runs", response_model=List[ApiTestRunSummaryOut])
def list_runs(
    project_id: Optional[int] = None,
    suite_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(ApiTestRun)
        .join(ApiTestSuite, ApiTestSuite.id == ApiTestRun.suite_id)
        .join(Project, Project.id == ApiTestSuite.project_id)
        .filter(Project.owner_id == current_user.id)
    )
    if project_id:
        _get_owned_project(db, project_id, current_user)
        query = query.filter(ApiTestSuite.project_id == project_id)
    if suite_id:
        _get_owned_executable_suite(db, suite_id, current_user)
        query = query.filter(ApiTestRun.suite_id == suite_id)
    runs = query.order_by(ApiTestRun.id.desc()).limit(100).all()
    return [_run_summary_out(db, run) for run in runs]


@router.get("/runs/{run_id}", response_model=ApiTestRunDetailOut)
def get_run_detail(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = (
        db.query(ApiTestRun)
        .join(ApiTestSuite, ApiTestSuite.id == ApiTestRun.suite_id)
        .join(Project, Project.id == ApiTestSuite.project_id)
        .filter(ApiTestRun.id == run_id, Project.owner_id == current_user.id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return _run_detail_out(db, run)


@router.delete("/runs/{run_id}")
def delete_run(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = (
        db.query(ApiTestRun)
        .join(ApiTestSuite, ApiTestSuite.id == ApiTestRun.suite_id)
        .join(Project, Project.id == ApiTestSuite.project_id)
        .filter(ApiTestRun.id == run_id, Project.owner_id == current_user.id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    db.delete(run)
    db.commit()
    return {"message": "删除成功"}


@router.get("/schedules", response_model=List[ApiScheduledTaskOut])
def list_schedules(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, current_user)
    tasks = (
        db.query(ApiScheduledTask)
        .filter(ApiScheduledTask.project_id == project_id)
        .order_by(ApiScheduledTask.id.desc())
        .all()
    )
    return [_schedule_out(db, task) for task in tasks]


@router.post("/schedules", response_model=ApiScheduledTaskOut)
def create_schedule(
    data: ApiScheduledTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_project(db, data.project_id, current_user)
    suite = _get_owned_executable_suite(db, data.suite_id, current_user)
    if suite.project_id != data.project_id:
        raise HTTPException(status_code=400, detail="套件与项目不匹配")
    try:
        validate_schedule_fields(
            schedule_type=data.schedule_type,
            run_time=data.run_time,
            week_day=data.week_day,
            interval_minutes=data.interval_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task = ApiScheduledTask(
        project_id=data.project_id,
        suite_id=data.suite_id,
        name=data.name.strip(),
        schedule_type=data.schedule_type,
        run_time=data.run_time or "09:00",
        week_day=data.week_day if data.schedule_type == "weekly" else None,
        interval_minutes=data.interval_minutes if data.schedule_type == "interval" else None,
        enabled=data.enabled,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    refresh_task_schedule(db, task, force_from_now=True)
    return _schedule_out(db, task)


@router.put("/schedules/{task_id}", response_model=ApiScheduledTaskOut)
def update_schedule(
    task_id: int,
    data: ApiScheduledTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_schedule(db, task_id, current_user)
    if data.suite_id is not None:
        suite = _get_owned_executable_suite(db, data.suite_id, current_user)
        if suite.project_id != task.project_id:
            raise HTTPException(status_code=400, detail="套件与项目不匹配")
        task.suite_id = data.suite_id
    if data.name is not None:
        task.name = data.name.strip()
    if data.schedule_type is not None:
        task.schedule_type = data.schedule_type
    if data.run_time is not None:
        task.run_time = data.run_time
    if data.week_day is not None:
        task.week_day = data.week_day
    if data.interval_minutes is not None:
        task.interval_minutes = data.interval_minutes
    if data.enabled is not None:
        task.enabled = data.enabled

    schedule_type = task.schedule_type
    if schedule_type != "weekly":
        task.week_day = None
    if schedule_type != "interval":
        task.interval_minutes = None

    try:
        validate_schedule_fields(
            schedule_type=schedule_type,
            run_time=task.run_time,
            week_day=task.week_day,
            interval_minutes=task.interval_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    db.refresh(task)
    refresh_task_schedule(db, task, force_from_now=True)
    return _schedule_out(db, task)


@router.post("/schedules/{task_id}/refresh", response_model=ApiScheduledTaskOut)
def refresh_schedule_next_run(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """根据当前时间重新计算下次执行；若已过期则在下一次调度检查时自动补跑。"""
    task = _get_owned_schedule(db, task_id, current_user)
    refresh_task_schedule(db, task, force_from_now=True)
    return _schedule_out(db, task)


@router.delete("/schedules/{task_id}")
def delete_schedule(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_schedule(db, task_id, current_user)
    db.delete(task)
    db.commit()
    return {"message": "删除成功"}


@router.post("/schedules/{task_id}/run-now", response_model=ApiRunTriggerOut)
def run_schedule_now(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_owned_schedule(db, task_id, current_user)
    execute_scheduled_task(db, task)
    db.refresh(task)
    if not task.last_run_id:
        raise HTTPException(status_code=400, detail="执行失败，请检查套件是否已配置环境")
    return ApiRunTriggerOut(run_id=task.last_run_id, message="定时任务已手动执行")


def _to_capture_item(data: dict) -> CaptureParsedItemOut:
    return CaptureParsedItemOut(
        name=data["name"],
        method=data["method"],
        path=data["path"],
        base_url=data["base_url"],
        full_url=data["full_url"],
        headers=data.get("headers") or "",
        body=data.get("body") or "",
        assertions=data.get("assertions") or "",
        source=data.get("source") or "fetch",
    )


def _ensure_environment(db: Session, project_id: int, base_url: str) -> ApiEnvironment:
    env = (
        db.query(ApiEnvironment)
        .filter(ApiEnvironment.project_id == project_id, ApiEnvironment.base_url == base_url)
        .first()
    )
    if env:
        return env
    from urllib.parse import urlparse

    host = urlparse(base_url).netloc or base_url
    env = ApiEnvironment(
        project_id=project_id,
        name=f"抓包环境-{host}",
        base_url=base_url,
        default_headers="{}",
        description="由抓包数据自动创建",
    )
    db.add(env)
    db.commit()
    db.refresh(env)
    return env


@router.post("/import/capture", response_model=CaptureImportOut)
def import_capture(
    data: CaptureImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    suite = _get_owned_executable_suite(db, data.suite_id, current_user)
    try:
        parsed_items = parse_multiple_captures(data.raw_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if data.case_name and len(parsed_items) == 1:
        parsed_items[0]["name"] = data.case_name.strip()

    preview_items = [_to_capture_item(item) for item in parsed_items]
    if data.preview:
        return CaptureImportOut(
            preview=True,
            items=preview_items,
            message=f"已解析 {len(preview_items)} 条接口，可确认导入",
        )

    environment_id = suite.environment_id
    if data.auto_environment and parsed_items:
        env = _ensure_environment(db, suite.project_id, parsed_items[0]["base_url"])
        environment_id = env.id
        if suite.environment_id != environment_id:
            suite.environment_id = environment_id
            db.commit()

    existing_count = db.query(ApiTestCase).filter(ApiTestCase.suite_id == suite.id).count()
    case_ids: List[int] = []
    for index, item in enumerate(parsed_items):
        case = ApiTestCase(
            suite_id=suite.id,
            name=item["name"],
            method=item["method"],
            path=item["path"],
            headers=item.get("headers") or None,
            body=item.get("body") or None,
            assertions=item.get("assertions") or None,
            sort_order=existing_count + index,
            enabled=True,
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        case_ids.append(case.id)

    return CaptureImportOut(
        preview=False,
        imported_count=len(case_ids),
        environment_id=environment_id,
        case_ids=case_ids,
        items=preview_items,
        message=f"成功导入 {len(case_ids)} 条接口用例",
    )

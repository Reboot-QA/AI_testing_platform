import json
import time
from typing import Any, Dict, Generator, List, Optional, Tuple
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from app.models.api_automation import (
    ApiEnvironment,
    ApiTestCase,
    ApiTestRun,
    ApiTestStepResult,
    ApiTestSuite,
)
from app.services.api_request_builder import (
    extract_meta_from_headers,
    iter_data_drive_variable_sets,
    prepare_case_request,
)
from app.services.api_variable_service import (
    apply_scoped_extractions,
    load_environment_variables,
    load_global_variables,
    merge_variable_context,
    persist_variable_context,
)
from app.services.apifox.assertions import _evaluate_assertion, _truncate_text
from app.services.apifox.response_extract import apply_response_extractors
from app.services.apifox.script_runner import resolve_pre_script, run_pre_script
from app.utils.time_util import now_local


def _loads_json(text: Optional[str], default: Any = None) -> Any:
    if not text:
        return default if default is not None else {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default if default is not None else {}


def _dumps_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _build_url(base_url: str, path: str) -> str:
    base = base_url.rstrip("/") + "/"
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urljoin(base, path.lstrip("/"))


def _merge_headers(default_headers: Dict[str, str], case_headers: Dict[str, str]) -> Dict[str, str]:
    merged = dict(default_headers or {})
    merged.update(case_headers or {})
    return merged


def _format_form_body(form_data: Dict[str, Any]) -> str:
    if not form_data:
        return ""
    return "\n".join(f"{key}={value}" for key, value in form_data.items())


def _execute_case(
    case: ApiTestCase,
    environment: Optional[ApiEnvironment],
    variables: Optional[Dict[str, str]] = None,
) -> Tuple[str, Dict[str, Any]]:
    meta = extract_meta_from_headers(case.headers)
    runtime_variables = dict(variables or {})

    pre_script, pre_script_lang = resolve_pre_script(meta)
    updated_variables, pre_script_logs, pre_script_error = run_pre_script(
        pre_script,
        pre_script_lang,
        runtime_variables,
    )
    if pre_script_error:
        return "failed", {
            "request": {
                "method": (case.method or "GET").upper(),
                "url": case.path or "",
                "headers": {},
                "body": case.body or "",
                "form_data": None,
            },
            "response_status": None,
            "response_headers": {},
            "response_body": "",
            "duration_ms": 0,
            "assertion_results": [
                {
                    "type": "pre_script",
                    "passed": False,
                    "expected": pre_script_lang,
                    "actual": pre_script_error,
                    "message": pre_script_error,
                }
            ],
            "extracted_variables": {},
            "scoped_extractions": [],
            "pre_script_logs": pre_script_logs,
            "error_message": pre_script_error,
        }

    method, url, headers, body, extra = prepare_case_request(
        case.headers,
        case.path,
        case.method,
        case.body,
        environment,
        variables=updated_variables,
    )
    form_data = extra.get("form_data")
    assertions = _loads_json(case.assertions, [])
    if not isinstance(assertions, list):
        assertions = []

    display_body = _format_form_body(form_data) if form_data else (body or "")

    request_snapshot = {
        "method": method,
        "url": url,
        "headers": headers,
        "body": display_body,
        "form_data": form_data,
    }

    start = time.perf_counter()
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            if form_data:
                files = {key: (None, value) for key, value in form_data.items()}
                response = client.request(method, url, headers=headers, files=files)
            else:
                response = client.request(method, url, headers=headers, content=body or None)
        duration_ms = (time.perf_counter() - start) * 1000
    except httpx.RequestError as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        return "failed", {
            "request": request_snapshot,
            "response_status": None,
            "response_headers": {},
            "response_body": "",
            "duration_ms": duration_ms,
            "assertion_results": [],
            "extracted_variables": {},
            "scoped_extractions": [],
            "pre_script_logs": pre_script_logs,
            "error_message": str(exc),
        }

    extracted_variables, scoped_items, extract_results = apply_response_extractors(
        meta.get("response_extract") or [],
        response,
        request=request_snapshot,
        duration_ms=duration_ms,
    )
    assertion_results = [_evaluate_assertion(item, response, duration_ms) for item in assertions]
    if not assertion_results:
        assertion_results = [
            {
                "type": "status_code",
                "passed": 200 <= response.status_code < 400,
                "expected": "2xx",
                "actual": response.status_code,
                "message": f"默认校验状态码 {response.status_code}",
            }
        ]

    passed = all(item.get("passed") for item in assertion_results)
    assertion_results.extend(extract_results)
    status = "passed" if passed else "failed"
    return status, {
        "request": request_snapshot,
        "response_status": response.status_code,
        "response_headers": dict(response.headers),
        "response_body": _truncate_text(response.text),
        "duration_ms": duration_ms,
        "assertion_results": assertion_results,
        "extracted_variables": extracted_variables,
        "scoped_extractions": scoped_items,
        "pre_script_logs": pre_script_logs,
        "error_message": None,
    }


def _iter_case_executions(case: ApiTestCase) -> List[Tuple[str, Optional[Dict[str, str]]]]:
    meta = extract_meta_from_headers(case.headers)
    return [(label, variables) for label, variables in iter_data_drive_variable_sets(meta)]


def iter_api_suite_run(
    db: Session, suite: ApiTestSuite, triggered_by: str = "manual"
) -> Generator[Dict[str, Any], None, None]:
    environment = suite.environment
    if not environment and suite.environment_id:
        environment = db.query(ApiEnvironment).filter(ApiEnvironment.id == suite.environment_id).first()
    if not environment:
        raise ValueError("测试套件未关联环境，请先配置执行环境")

    cases = (
        db.query(ApiTestCase)
        .filter(ApiTestCase.suite_id == suite.id, ApiTestCase.enabled.is_(True))
        .order_by(ApiTestCase.sort_order.asc(), ApiTestCase.id.asc())
        .all()
    )

    total_steps = 0
    for case in cases:
        if not case.enabled:
            continue
        total_steps += len(_iter_case_executions(case))

    run = ApiTestRun(
        suite_id=suite.id,
        status="running",
        total_count=total_steps or len(cases),
        triggered_by=triggered_by,
        started_at=now_local(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    yield {
        "type": "start",
        "run_id": run.id,
        "total": total_steps,
        "message": f"开始执行套件「{suite.name}」，共 {total_steps} 个步骤",
    }

    passed_count = 0
    failed_count = 0
    skipped_count = 0
    run_started = time.perf_counter()
    runtime_variables: Dict[str, str] = {}
    global_variables = load_global_variables(db, suite.project_id)
    env_variables = load_environment_variables(environment)
    step_index = 0

    for case in cases:
        if not case.enabled:
            skipped_count += 1
            continue

        iterations = _iter_case_executions(case)
        for data_label, variables in iterations:
            merged_variables = merge_variable_context(
                global_variables,
                env_variables,
                runtime_variables,
                variables or {},
            )
            status, detail = _execute_case(case, environment, variables=merged_variables)
            apply_scoped_extractions(
                detail.get("scoped_extractions") or [],
                runtime_variables,
                env_variables,
                global_variables,
            )
            if status == "passed":
                passed_count += 1
            else:
                failed_count += 1

            case_name = case.name
            if len(iterations) > 1:
                case_name = f"{case.name} [{data_label}]"

            step = ApiTestStepResult(
                run_id=run.id,
                case_id=case.id,
                case_name=case_name,
                method=detail["request"]["method"],
                url=detail["request"]["url"],
                status=status,
                duration_ms=detail["duration_ms"],
                request_headers=_dumps_json(detail["request"]["headers"]),
                request_body=detail["request"]["body"] or "",
                response_status=detail["response_status"],
                response_headers=_dumps_json(detail["response_headers"]),
                response_body=detail["response_body"],
                assertion_results=_dumps_json(detail["assertion_results"]),
                error_message=detail["error_message"],
            )
            db.add(step)
            db.commit()

            step_index += 1
            yield {
                "type": "step",
                "index": step_index,
                "total": total_steps,
                "case_name": case_name,
                "method": detail["request"]["method"],
                "status": status,
                "duration_ms": detail["duration_ms"],
                "response_status": detail.get("response_status"),
                "error_message": detail.get("error_message"),
            }

    elapsed_ms = (time.perf_counter() - run_started) * 1000
    total = passed_count + failed_count + skipped_count
    pass_rate = round((passed_count / total) * 100, 2) if total else 0.0
    run.status = "passed" if failed_count == 0 and total > 0 else ("failed" if failed_count else "passed")
    if total == 0:
        run.status = "passed"
    run.passed_count = passed_count
    run.failed_count = failed_count
    run.skipped_count = skipped_count
    run.duration_ms = round(elapsed_ms, 2)
    run.pass_rate = pass_rate
    run.finished_at = now_local()
    persist_variable_context(db, environment, env_variables, global_variables)
    db.commit()
    db.refresh(run)

    yield {
        "type": "done",
        "run_id": run.id,
        "status": run.status,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "skipped_count": skipped_count,
        "pass_rate": pass_rate,
        "duration_ms": run.duration_ms,
        "message": (
            f"执行完成：通过 {passed_count}，失败 {failed_count}，"
            f"通过率 {pass_rate}%，耗时 {round(run.duration_ms / 1000, 2)}s"
        ),
    }


def run_api_suite(db: Session, suite: ApiTestSuite, triggered_by: str = "manual") -> ApiTestRun:
    done_event = None
    for event in iter_api_suite_run(db, suite, triggered_by):
        if event.get("type") == "done":
            done_event = event
    if not done_event:
        raise RuntimeError("套件执行未返回结果")
    run = db.query(ApiTestRun).filter(ApiTestRun.id == done_event["run_id"]).first()
    if not run:
        raise RuntimeError("套件执行记录不存在")
    return run

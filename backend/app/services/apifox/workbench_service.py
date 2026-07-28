"""Apifox 工作台 · 业务层（组装跨项目概览：统计磁贴 / 我的项目 / 运行中 / 最近报告）。"""

from datetime import datetime
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import User
from app.repositories.apifox import workbench_repo
from app.services import user_project_pref_service
from app.services.project_access_service import accessible_projects_query, is_admin


def _today_start() -> datetime:
    # 与 run.started_at 的 utcnow 口径对齐，取 UTC 零点
    now = datetime.utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _role_of(project: Project, user: User) -> str:
    if is_admin(user):
        return "管理员"
    if project.owner_id == user.id:
        return "负责人"
    return "成员"


def _project_context(db: Session, user: User) -> Tuple[List[Project], List[int], Dict[int, str], Dict[int, str]]:
    projects = accessible_projects_query(db, user).all()
    project_ids = [p.id for p in projects]
    project_name = {p.id: p.name for p in projects}
    env_names = workbench_repo.environment_names(db, project_ids)
    return projects, project_ids, project_name, env_names


def _running_out(runs, project_name: Dict[int, str], env_names: Dict[int, str]) -> List[dict]:
    return [
        {
            "run_id": r.id,
            "project_id": r.project_id,
            "project_name": project_name.get(r.project_id, ""),
            "target_type": r.target_type,
            "target_name": r.target_name,
            "environment_name": env_names.get(r.environment_id),
            "started_at": r.started_at,
        }
        for r in runs
    ]


def _report_out(
    runs, project_name: Dict[int, str], env_names: Dict[int, str], reasons: Dict[int, str]
) -> List[dict]:
    return [
        {
            "run_id": r.id,
            "project_id": r.project_id,
            "project_name": project_name.get(r.project_id, ""),
            "target_type": r.target_type,
            "target_name": r.target_name,
            "environment_name": env_names.get(r.environment_id),
            "status": r.status,
            "passed_count": r.passed_count,
            "total_count": r.total_count,
            "pass_rate": r.pass_rate,
            "started_at": r.started_at,
            "error_message": reasons.get(r.id) if r.status == "failed" else None,
        }
        for r in runs
    ]


def get_project_stats(db: Session, project_id: int) -> dict:
    """单项目仪表板统计：counts + 今日通过率 + 近 7 天趋势（含今天，按日升序，缺日补零）。"""
    from datetime import timedelta

    pids = [project_id]
    endpoint = workbench_repo.count_endpoints(db, pids).get(project_id, 0)
    case = workbench_repo.count_cases(db, pids).get(project_id, 0)
    scenario = workbench_repo.count_scenarios(db, pids).get(project_id, 0)
    suite = workbench_repo.count_suites(db, pids).get(project_id, 0)
    running = workbench_repo.count_running(db, pids)
    passed_sum, total_sum = workbench_repo.today_totals(db, pids, _today_start())

    trend_map = workbench_repo.daily_trend(db, project_id, 7)
    today = datetime.utcnow().date()
    trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        key = day.isoformat()
        passed, total = trend_map.get(key, (0, 0))
        trend.append(
            {
                "date": key,
                "passed": passed,
                "failed": max(total - passed, 0),
                "total": total,
                "pass_rate": round(passed / total * 100, 1) if total else None,
            }
        )

    return {
        "endpoint_count": endpoint,
        "case_count": case,
        "scenario_count": scenario,
        "suite_count": suite,
        "running_count": running,
        "today_pass_rate": round(passed_sum / total_sum * 100, 1) if total_sum else None,
        "trend": trend,
    }


def get_overview(db: Session, user: User) -> dict:
    projects, project_ids, project_name, env_names = _project_context(db, user)

    endpoint_cnt = workbench_repo.count_endpoints(db, project_ids)
    scenario_cnt = workbench_repo.count_scenarios(db, project_ids)
    case_cnt = workbench_repo.count_cases(db, project_ids)
    running_count = workbench_repo.count_running(db, project_ids)
    passed_sum, total_sum = workbench_repo.today_totals(db, project_ids, _today_start())

    stats = {
        "project_count": len(projects),
        "endpoint_count": sum(endpoint_cnt.values()),
        "scenario_count": sum(scenario_cnt.values()),
        "running_count": running_count,
        "today_pass_rate": round(passed_sum / total_sum * 100, 1) if total_sum else None,
    }

    project_cards = [
        {
            "id": p.id,
            "owner_seq": p.owner_seq or 0,
            "name": p.name,
            "description": p.description,
            "endpoint_count": endpoint_cnt.get(p.id, 0),
            "scenario_count": scenario_cnt.get(p.id, 0),
            "case_count": case_cnt.get(p.id, 0),
            "role": _role_of(p, user),
        }
        for p in projects
    ]
    project_cards = user_project_pref_service.order_cards(db, user.id, project_cards)

    return {
        "stats": stats,
        "projects": project_cards,
    }


def list_running_page(db: Session, user: User, page: int, page_size: int) -> dict:
    _, project_ids, project_name, env_names = _project_context(db, user)
    total = workbench_repo.count_running(db, project_ids)
    runs = workbench_repo.list_running_page(db, project_ids, page, page_size)
    return {
        "items": _running_out(runs, project_name, env_names),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def list_reports_page(
    db: Session,
    user: User,
    page: int,
    page_size: int,
    status: str | None = None,
    target_type: str | None = None,
) -> dict:
    _, project_ids, project_name, env_names = _project_context(db, user)
    total = workbench_repo.count_runs(db, project_ids, status, target_type)
    runs = workbench_repo.recent_runs_page(db, project_ids, page, page_size, status, target_type)
    reasons = workbench_repo.failure_reasons(db, [r.id for r in runs if r.status == "failed"])
    return {
        "items": _report_out(runs, project_name, env_names, reasons),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def list_failures_page(db: Session, user: User, page: int, page_size: int) -> dict:
    """跨项目「失败聚焦」：最近失败运行 + 失败原因（首个失败步骤 error_message）。"""
    _, project_ids, project_name, env_names = _project_context(db, user)
    total = workbench_repo.count_failures(db, project_ids)
    runs = workbench_repo.list_failures_page(db, project_ids, page, page_size)
    reasons = workbench_repo.failure_reasons(db, [r.id for r in runs])
    return {
        "items": _report_out(runs, project_name, env_names, reasons),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def list_schedules_page(db: Session, user: User, page: int, page_size: int) -> dict:
    """跨项目即将执行的定时任务（启用且有 next_run_at，按 next_run_at 升序）。"""
    _, project_ids, project_name, _ = _project_context(db, user)
    total = workbench_repo.count_schedules(db, project_ids)
    schedules = workbench_repo.list_schedules_page(db, project_ids, page, page_size)
    items = [
        {
            "schedule_id": s.id,
            "project_id": s.project_id,
            "project_name": project_name.get(s.project_id, ""),
            "name": s.name,
            "target_type": s.target_type,
            "schedule_type": s.schedule_type,
            "next_run_at": s.next_run_at,
            "last_run_status": s.last_run_status,
        }
        for s in schedules
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_manual_page(db: Session, user: User, page: int, page_size: int) -> dict:
    """跨项目手工测试单（最近在前）。"""
    _, project_ids, project_name, _ = _project_context(db, user)
    total = workbench_repo.count_manual_runs(db, project_ids)
    runs = workbench_repo.list_manual_runs_page(db, project_ids, page, page_size)
    items = [
        {
            "run_id": r.id,
            "project_id": r.project_id,
            "project_name": project_name.get(r.project_id, ""),
            "name": r.name,
            "status": r.status,
            "passed_count": r.passed_count,
            "failed_count": r.failed_count,
            "total_count": r.total_count,
            "created_at": r.created_at,
        }
        for r in runs
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}

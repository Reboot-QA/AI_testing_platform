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


def _report_out(runs, project_name: Dict[int, str], env_names: Dict[int, str]) -> List[dict]:
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
        }
        for r in runs
    ]


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
            "name": p.name,
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


def list_reports_page(db: Session, user: User, page: int, page_size: int) -> dict:
    _, project_ids, project_name, env_names = _project_context(db, user)
    total = workbench_repo.count_runs(db, project_ids)
    runs = workbench_repo.recent_runs_page(db, project_ids, page, page_size)
    return {
        "items": _report_out(runs, project_name, env_names),
        "total": total,
        "page": page,
        "page_size": page_size,
    }

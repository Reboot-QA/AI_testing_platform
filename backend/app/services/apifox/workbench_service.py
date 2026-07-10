"""Apifox 工作台 · 业务层（组装跨项目概览：统计磁贴 / 我的项目 / 运行中 / 最近报告）。"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.user import User
from app.repositories.apifox import workbench_repo
from app.services.project_access_service import accessible_projects_query, is_admin

_RECENT_REPORTS_LIMIT = 10


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


def get_overview(db: Session, user: User) -> dict:
    projects = accessible_projects_query(db, user).all()
    project_ids = [p.id for p in projects]
    project_name = {p.id: p.name for p in projects}

    endpoint_cnt = workbench_repo.count_endpoints(db, project_ids)
    scenario_cnt = workbench_repo.count_scenarios(db, project_ids)
    case_cnt = workbench_repo.count_cases(db, project_ids)
    env_names = workbench_repo.environment_names(db, project_ids)
    running = workbench_repo.list_running(db, project_ids)
    recent = workbench_repo.recent_runs(db, project_ids, _RECENT_REPORTS_LIMIT)
    passed_sum, total_sum = workbench_repo.today_totals(db, project_ids, _today_start())

    stats = {
        "project_count": len(projects),
        "endpoint_count": sum(endpoint_cnt.values()),
        "scenario_count": sum(scenario_cnt.values()),
        "running_count": len(running),
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

    running_out = [
        {
            "run_id": r.id,
            "project_id": r.project_id,
            "project_name": project_name.get(r.project_id, ""),
            "target_type": r.target_type,
            "target_name": r.target_name,
            "environment_name": env_names.get(r.environment_id),
            "started_at": r.started_at,
        }
        for r in running
    ]

    recent_out = [
        {
            "run_id": r.id,
            "project_id": r.project_id,
            "project_name": project_name.get(r.project_id, ""),
            "target_name": r.target_name,
            "environment_name": env_names.get(r.environment_id),
            "status": r.status,
            "passed_count": r.passed_count,
            "total_count": r.total_count,
            "pass_rate": r.pass_rate,
            "started_at": r.started_at,
        }
        for r in recent
    ]

    return {
        "stats": stats,
        "projects": project_cards,
        "running": running_out,
        "recent_reports": recent_out,
    }

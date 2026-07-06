import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.api_automation import ApiEnvironment
from app.models.project import Project

VALID_SCOPES = frozenset({"temporary", "environment", "global"})
DEFAULT_SCOPE = "temporary"
LEGACY_DEFAULT_SCOPE = "temporary"


def normalize_scope(scope: Optional[str]) -> str:
    normalized = (scope or LEGACY_DEFAULT_SCOPE).lower().strip()
    return normalized if normalized in VALID_SCOPES else LEGACY_DEFAULT_SCOPE


def load_variables_json(text: Optional[str]) -> Dict[str, str]:
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): "" if value is None else str(value) for key, value in parsed.items() if str(key).strip()}


def dump_variables_json(variables: Dict[str, str]) -> str:
    return json.dumps(variables or {}, ensure_ascii=False)


def merge_variable_context(
    global_vars: Optional[Dict[str, str]] = None,
    env_vars: Optional[Dict[str, str]] = None,
    runtime_vars: Optional[Dict[str, str]] = None,
    case_vars: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    for source in (global_vars, env_vars, runtime_vars, case_vars):
        if source:
            merged.update(source)
    return merged


def apply_scoped_extractions(
    scoped_items: List[Dict[str, str]],
    runtime_vars: Dict[str, str],
    env_vars: Dict[str, str],
    global_vars: Dict[str, str],
) -> Dict[str, str]:
    extracted: Dict[str, str] = {}
    for item in scoped_items or []:
        key = (item.get("key") or "").strip()
        if not key:
            continue
        value = item.get("value") or ""
        scope = normalize_scope(item.get("scope"))
        extracted[key] = value
        if scope == "temporary":
            runtime_vars[key] = value
        elif scope == "environment":
            runtime_vars[key] = value
            env_vars[key] = value
        elif scope == "global":
            runtime_vars[key] = value
            global_vars[key] = value
    return extracted


def load_global_variables(db: Session, project_id: int) -> Dict[str, str]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {}
    return load_variables_json(getattr(project, "api_global_variables", None))


def save_global_variables(db: Session, project_id: int, variables: Dict[str, str]) -> None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return
    project.api_global_variables = dump_variables_json(variables)
    db.commit()


def load_environment_variables(environment: Optional[ApiEnvironment]) -> Dict[str, str]:
    if not environment:
        return {}
    return load_variables_json(getattr(environment, "variables", None))


def save_environment_variables(db: Session, environment: ApiEnvironment, variables: Dict[str, str]) -> None:
    environment.variables = dump_variables_json(variables)
    db.commit()


def persist_variable_context(
    db: Session,
    environment: Optional[ApiEnvironment],
    env_vars: Dict[str, str],
    global_vars: Dict[str, str],
) -> None:
    changed = False
    if environment is not None:
        environment.variables = dump_variables_json(env_vars)
        changed = True
    if environment is not None:
        project = db.query(Project).filter(Project.id == environment.project_id).first()
        if project is not None:
            project.api_global_variables = dump_variables_json(global_vars)
            changed = True
    if changed:
        db.commit()

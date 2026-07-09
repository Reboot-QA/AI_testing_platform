from app.routers.apifox.cases import router as cases_router
from app.routers.apifox.data_models import router as data_models_router
from app.routers.apifox.endpoints import router
from app.routers.apifox.global_params import router as global_params_router
from app.routers.apifox.imports import router as imports_router
from app.routers.apifox.runs import router as runs_router
from app.routers.apifox.scenarios import router as scenarios_router
from app.routers.apifox.schedules import router as schedules_router
from app.routers.apifox.scripts import router as scripts_router
from app.routers.apifox.variables import router as variables_router

__all__ = [
    "router",
    "variables_router",
    "cases_router",
    "data_models_router",
    "scripts_router",
    "global_params_router",
    "scenarios_router",
    "runs_router",
    "imports_router",
    "schedules_router",
]

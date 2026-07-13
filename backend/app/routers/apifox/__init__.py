from app.routers.apifox.cases import router as cases_router
from app.routers.apifox.data_models import router as data_models_router
from app.routers.apifox.databases import router as databases_router
from app.routers.apifox.datasets import router as datasets_router
from app.routers.apifox.debug import router as debug_router
from app.routers.apifox.endpoints import router
from app.routers.apifox.global_params import router as global_params_router
from app.routers.apifox.imports import router as imports_router
from app.routers.apifox.runs import router as runs_router
from app.routers.apifox.scenarios import router as scenarios_router
from app.routers.apifox.schedules import router as schedules_router
from app.routers.apifox.scripts import router as scripts_router
from app.routers.apifox.suites import router as suites_router
from app.routers.apifox.variables import router as variables_router
from app.routers.apifox.workbench import router as workbench_router

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
    "debug_router",
    "workbench_router",
    "suites_router",
    "datasets_router",
    "databases_router",
]

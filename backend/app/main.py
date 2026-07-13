from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.bootstrap import run_bootstrap
from app.config import settings
from app.routers import auth, projects, requirements, testcases, users, api_automation, test_execution, logs, departments, assistant
from app.routers import settings as settings_router
from app.routers.apifox import router as apifox_router
from app.routers.apifox import variables_router as apifox_variables_router
from app.routers.apifox import cases_router as apifox_cases_router
from app.routers.apifox import data_models_router as apifox_data_models_router
from app.routers.apifox import global_params_router as apifox_global_params_router
from app.routers.apifox import imports_router as apifox_imports_router
from app.routers.apifox import runs_router as apifox_runs_router
from app.routers.apifox import scenarios_router as apifox_scenarios_router
from app.routers.apifox import schedules_router as apifox_schedules_router
from app.routers.apifox import debug_router as apifox_debug_router
from app.routers.apifox import scripts_router as apifox_scripts_router
from app.routers.apifox import workbench_router as apifox_workbench_router
from app.routers.apifox import suites_router as apifox_suites_router
from app.services.schedule_service import start_scheduler, stop_scheduler
from app.request_logging import register_request_logging


def setup_logging() -> None:
    """配置日志输出到 stdout，由 deploy.sh 以追加方式写入 backend.log，部署时不覆盖历史。"""
    project_root = Path(__file__).resolve().parent.parent.parent
    log_dir = Path(settings.log_dir) if settings.log_dir else project_root / ".deploy" / "logs"
    if not log_dir.is_absolute():
        log_dir = (project_root / log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    backend_log = log_dir / "backend.log"
    file_handler = logging.FileHandler(backend_log, encoding="utf-8")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


_app_ready = False
_app_init_error: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _app_ready, _app_init_error
    setup_logging()
    _app_ready = False
    _app_init_error = None
    try:
        if os.environ.get("APP_BOOTSTRAP_DONE") != "1":
            run_bootstrap()
        start_scheduler()
        _app_ready = True
        logging.getLogger(__name__).info("应用启动完成")
    except Exception as exc:
        _app_init_error = str(exc)
        logging.getLogger(__name__).exception("应用启动失败")
        raise
    yield
    stop_scheduler()
    _app_ready = False


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(requirements.router, prefix="/api/v1")
app.include_router(testcases.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(departments.router, prefix="/api/v1")
app.include_router(api_automation.router, prefix="/api/v1")
app.include_router(test_execution.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")
app.include_router(assistant.router, prefix="/api/v1")
app.include_router(apifox_router, prefix="/api/v1")
app.include_router(apifox_variables_router, prefix="/api/v1")
app.include_router(apifox_cases_router, prefix="/api/v1")
app.include_router(apifox_data_models_router, prefix="/api/v1")
app.include_router(apifox_scripts_router, prefix="/api/v1")
app.include_router(apifox_global_params_router, prefix="/api/v1")
app.include_router(apifox_scenarios_router, prefix="/api/v1")
app.include_router(apifox_runs_router, prefix="/api/v1")
app.include_router(apifox_imports_router, prefix="/api/v1")
app.include_router(apifox_schedules_router, prefix="/api/v1")
app.include_router(apifox_debug_router, prefix="/api/v1")
app.include_router(apifox_workbench_router, prefix="/api/v1")
app.include_router(apifox_suites_router, prefix="/api/v1")

register_request_logging(app)


@app.get("/health")
def health():
    if _app_init_error:
        raise HTTPException(status_code=500, detail=_app_init_error)
    if not _app_ready:
        raise HTTPException(status_code=503, detail="starting")
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "AI质量平台 API", "docs": "/docs"}

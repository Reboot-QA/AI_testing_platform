from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, projects, requirements, testcases, users, api_automation, test_execution, logs
from app.routers import settings as settings_router
from app.services.seed import seed_demo_data
from app.services.settings_service import init_llm_settings_from_env
from app.services.api_automation_migration import migrate_api_test_suite_tree
from app.services.permission_service import migrate_all_user_permissions
from app.services.schedule_service import init_schedules_on_startup, start_scheduler, stop_scheduler


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

    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo_data(db)
        init_llm_settings_from_env(db)
        migrate_api_test_suite_tree(db)
        migrate_all_user_permissions(db)
        init_schedules_on_startup(db)
    finally:
        db.close()
    start_scheduler()
    yield
    stop_scheduler()


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
app.include_router(api_automation.router, prefix="/api/v1")
app.include_router(test_execution.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "AI质量平台 API", "docs": "/docs"}

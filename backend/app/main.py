from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, projects, requirements, testcases, users, api_automation, test_execution
from app.routers import settings as settings_router
from app.services.seed import seed_demo_data
from app.services.settings_service import init_llm_settings_from_env
from app.services.api_automation_migration import migrate_api_test_suite_tree
from app.services.permission_service import migrate_all_user_permissions
from app.services.schedule_service import init_schedules_on_startup, start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/")
def root():
    return {"message": "AI质量平台 API", "docs": "/docs"}

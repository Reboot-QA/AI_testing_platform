import logging

from app.database import Base, SessionLocal, engine
from app.services.api_automation_migration import (
    migrate_api_scheduled_task_suites,
    migrate_api_test_suite_tree,
    migrate_api_variable_stores,
    migrate_department_permissions,
    migrate_requirement_created_by,
    migrate_testcase_created_by,
)
from app.services.permission_service import migrate_all_user_permissions
from app.services.schedule_service import init_schedules_on_startup
from app.services.seed import seed_demo_data
from app.services.settings_service import init_llm_settings_from_env
from app.services.user_migration import migrate_user_optional_email

logger = logging.getLogger(__name__)


def run_bootstrap() -> None:
    """启动前数据库初始化与迁移（Docker entrypoint 与 uvicorn lifespan 均可调用，幂等）。"""
    steps = [
        ("初始化数据库表", lambda db: Base.metadata.create_all(bind=engine)),
        ("迁移接口套件树", migrate_api_test_suite_tree),
        ("迁移接口变量", migrate_api_variable_stores),
        ("迁移定时任务套件", migrate_api_scheduled_task_suites),
        ("迁移部门权限", migrate_department_permissions),
        ("迁移需求创建人", migrate_requirement_created_by),
        ("迁移用例创建人", migrate_testcase_created_by),
        ("迁移用户邮箱", lambda db: migrate_user_optional_email()),
        ("写入演示数据", seed_demo_data),
        ("加载 LLM 配置", init_llm_settings_from_env),
        ("迁移菜单权限", migrate_all_user_permissions),
        ("初始化定时任务", init_schedules_on_startup),
    ]

    import app.models  # noqa: F401

    db = SessionLocal()
    try:
        for label, step in steps:
            logger.info("启动步骤: %s", label)
            step(db)
    finally:
        db.close()
    logger.info("数据库初始化完成")

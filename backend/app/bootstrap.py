import logging

from app.database import Base, SessionLocal, engine
from app.services.api_automation_migration import (
    drop_legacy_api_automation_tables,
    migrate_department_permissions,
    migrate_requirement_created_by,
    migrate_requirement_sort_order,
    migrate_testcase_created_by,
    migrate_testcase_sort_order,
)
from app.services.apifox.ai_gen_worker import init_ai_gen_tasks_on_startup
from app.services.apifox.migration import (
    migrate_apifox_assertion_operator,
    migrate_apifox_ai_gen_discarded_cases,
    migrate_apifox_case_category,
    migrate_apifox_case_origin,
    migrate_apifox_deleted_by,
    migrate_apifox_endpoint_cases_stale,
    migrate_apifox_endpoint_contract,
    migrate_apifox_endpoint_server_name,
    migrate_apifox_folder_kind,
    migrate_apifox_notify_retry,
    migrate_apifox_optimistic_version,
    migrate_apifox_ordered_processors,
    migrate_apifox_run_iteration,
    migrate_apifox_run_parent,
    migrate_apifox_run_step_contract,
    migrate_apifox_run_step_depth,
    migrate_apifox_run_step_warnings,
    migrate_apifox_scenario_folder,
    migrate_apifox_scenario_priority,
    migrate_apifox_scenario_run_config,
    migrate_apifox_scenario_step_tree,
    migrate_apifox_schedule_cron,
    migrate_apifox_soft_delete,
)
from app.services.apifox.run_service import recover_orphan_runs
from app.services.apifox.scheduler import init_schedules_on_startup
from app.services.permission_service import migrate_all_user_permissions
from app.services.project_migration import (
    migrate_project_last_import_url,
    migrate_project_members_columns,
    migrate_project_owner_seq,
)
from app.services.seed import seed_demo_data
from app.services.settings_service import init_llm_settings_from_env
from app.services.user_migration import (
    migrate_user_login_lock,
    migrate_user_must_change_password,
    migrate_user_optional_email,
)

logger = logging.getLogger(__name__)


def run_bootstrap() -> None:
    """启动前数据库初始化与迁移（Docker entrypoint 与 uvicorn lifespan 均可调用，幂等）。"""
    steps = [
        ("初始化数据库表", lambda db: Base.metadata.create_all(bind=engine)),
        ("迁移项目负责人序号", migrate_project_owner_seq),
        ("清除老接口自动化遗留表", drop_legacy_api_automation_tables),
        ("迁移用户邮箱", lambda db: migrate_user_optional_email()),
        ("迁移用户强制改密标记", migrate_user_must_change_password),
        ("迁移用户登录锁定字段", migrate_user_login_lock),
        ("迁移部门权限", migrate_department_permissions),
        ("迁移需求创建人", migrate_requirement_created_by),
        ("迁移需求展示序号", migrate_requirement_sort_order),
        ("迁移用例创建人", migrate_testcase_created_by),
        ("迁移用例展示序号", migrate_testcase_sort_order),
        ("迁移接口前置URL名列", migrate_apifox_endpoint_server_name),
        ("迁移断言操作符列", migrate_apifox_assertion_operator),
        ("迁移接口响应契约列", migrate_apifox_endpoint_contract),
        ("迁移运行步骤契约结果列", migrate_apifox_run_step_contract),
        ("迁移场景步骤树列", migrate_apifox_scenario_step_tree),
        ("迁移运行步骤深度列", migrate_apifox_run_step_depth),
        ("迁移运行父运行列", migrate_apifox_run_parent),
        ("迁移乐观锁版本列", migrate_apifox_optimistic_version),
        ("迁移场景运行配置列", migrate_apifox_scenario_run_config),
        ("迁移用例分类列", migrate_apifox_case_category),
        ("迁移用例来源列", migrate_apifox_case_origin),
        ("迁移运行轮次列", migrate_apifox_run_iteration),
        ("迁移定时任务cron列", migrate_apifox_schedule_cron),
        ("迁移场景优先级列", migrate_apifox_scenario_priority),
        ("迁移文件夹kind列", migrate_apifox_folder_kind),
        ("迁移场景文件夹列", migrate_apifox_scenario_folder),
        ("迁移运行步骤告警列", migrate_apifox_run_step_warnings),
        ("迁移失败通知重试列", migrate_apifox_notify_retry),
        ("迁移AI生成废弃预览列", migrate_apifox_ai_gen_discarded_cases),
        ("迁移有序处理器列", migrate_apifox_ordered_processors),
        ("迁移接口用例待复核列", migrate_apifox_endpoint_cases_stale),
        ("迁移软删除回收站列", migrate_apifox_soft_delete),
        ("迁移软删除操作人列", migrate_apifox_deleted_by),
        ("迁移项目成员列", migrate_project_members_columns),
        ("迁移项目上次导入URL列", migrate_project_last_import_url),
        ("写入演示数据", seed_demo_data),
        ("加载 LLM 配置", init_llm_settings_from_env),
        ("迁移菜单权限", migrate_all_user_permissions),
        ("初始化定时任务", init_schedules_on_startup),
        ("恢复残留AI生成任务", init_ai_gen_tasks_on_startup),
        ("回收残留运行", lambda db: recover_orphan_runs(db)),
    ]

    import app.models  # noqa: F401

    db = SessionLocal()
    try:
        for label, step in steps:
            logger.info("启动步骤: %s", label)
            step(db)
            logger.info("启动步骤完成: %s", label)
    finally:
        db.close()
    logger.info("数据库初始化完成")

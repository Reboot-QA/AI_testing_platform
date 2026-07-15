"""删除项目前清空其全部数据（FK 安全顺序：子表先于父表）。不提交事务（调用方 commit）。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.api_automation import (
    ApiEnvironment,
    ApiScheduledTask,
    ApiScheduledTaskSuite,
    ApiTestCase,
    ApiTestRun,
    ApiTestStepResult,
    ApiTestSuite,
)
from app.models.apifox.case import ApifoxCaseAssertion, ApifoxCaseExtract, ApifoxEndpointCase
from app.models.apifox.data_model import ApifoxSchema
from app.models.apifox.database_conn import ApifoxEnvironmentDatabase
from app.models.apifox.dataset import ApifoxDataset, ApifoxDatasetRow
from app.models.apifox.endpoint import (
    ApifoxEndpoint,
    ApifoxEndpointAssertion,
    ApifoxEndpointExtract,
    ApifoxFolder,
)
from app.models.apifox.global_param import ApifoxGlobalParam
from app.models.apifox.run import ApifoxRun, ApifoxRunStep
from app.models.apifox.scenario import ApifoxScenario, ApifoxScenarioStep
from app.models.apifox.schedule import ApifoxSchedule
from app.models.apifox.script import ApifoxCaseScript, ApifoxEndpointScript, ApifoxScript
from app.models.apifox.suite import ApifoxSuite, ApifoxSuiteItem
from app.models.apifox.upload_file import ApifoxUploadFile
from app.models.apifox.variable import (
    ApifoxEnvironment,
    ApifoxEnvironmentServer,
    ApifoxEnvironmentVariable,
    ApifoxEnvironmentVarLocal,
    ApifoxGlobalVariable,
    ApifoxGlobalVarLocal,
)
from app.models.requirement import Requirement
from app.models.test_execution import ManualTestRun, ManualTestRunCase
from app.models.testcase import TestCase


def purge_project_apifox(db: Session, project_id: int) -> None:
    """按 FK 依赖倒序清空该项目所有 apifox 表数据。用批量删，不 commit。"""
    run_ids = select(ApifoxRun.id).where(ApifoxRun.project_id == project_id)
    scen_ids = select(ApifoxScenario.id).where(ApifoxScenario.project_id == project_id)
    suite_ids = select(ApifoxSuite.id).where(ApifoxSuite.project_id == project_id)
    dataset_ids = select(ApifoxDataset.id).where(ApifoxDataset.project_id == project_id)
    case_ids = select(ApifoxEndpointCase.id).where(ApifoxEndpointCase.project_id == project_id)
    ep_ids = select(ApifoxEndpoint.id).where(ApifoxEndpoint.project_id == project_id)
    env_ids = select(ApifoxEnvironment.id).where(ApifoxEnvironment.project_id == project_id)
    envvar_ids = select(ApifoxEnvironmentVariable.id).where(
        ApifoxEnvironmentVariable.environment_id.in_(env_ids)
    )
    gvar_ids = select(ApifoxGlobalVariable.id).where(ApifoxGlobalVariable.project_id == project_id)

    def wipe(model, cond) -> None:
        db.query(model).filter(cond).delete(synchronize_session=False)

    # 运行记录（先断 parent_run_id 自引用再删，避免 InnoDB 逐行 FK 检查报错，同 ApifoxFolder 范式）
    db.query(ApifoxRun).filter(ApifoxRun.project_id == project_id).update(
        {ApifoxRun.parent_run_id: None}, synchronize_session=False
    )
    wipe(ApifoxRunStep, ApifoxRunStep.run_id.in_(run_ids))
    wipe(ApifoxRun, ApifoxRun.project_id == project_id)
    # 测试套件
    wipe(ApifoxSuiteItem, ApifoxSuiteItem.suite_id.in_(suite_ids))
    wipe(ApifoxSuite, ApifoxSuite.project_id == project_id)
    # 项目级数据集
    wipe(ApifoxDatasetRow, ApifoxDatasetRow.dataset_id.in_(dataset_ids))
    wipe(ApifoxDataset, ApifoxDataset.project_id == project_id)
    # 场景
    wipe(ApifoxScenarioStep, ApifoxScenarioStep.scenario_id.in_(scen_ids))
    wipe(ApifoxScenario, ApifoxScenario.project_id == project_id)
    # 用例及其处理器
    wipe(ApifoxCaseAssertion, ApifoxCaseAssertion.case_id.in_(case_ids))
    wipe(ApifoxCaseExtract, ApifoxCaseExtract.case_id.in_(case_ids))
    wipe(ApifoxCaseScript, ApifoxCaseScript.case_id.in_(case_ids))
    wipe(ApifoxEndpointCase, ApifoxEndpointCase.project_id == project_id)
    # 接口及其处理器
    wipe(ApifoxEndpointAssertion, ApifoxEndpointAssertion.endpoint_id.in_(ep_ids))
    wipe(ApifoxEndpointExtract, ApifoxEndpointExtract.endpoint_id.in_(ep_ids))
    wipe(ApifoxEndpointScript, ApifoxEndpointScript.endpoint_id.in_(ep_ids))
    wipe(ApifoxEndpoint, ApifoxEndpoint.project_id == project_id)
    # 文件夹（先断自引用再删）
    db.query(ApifoxFolder).filter(ApifoxFolder.project_id == project_id).update(
        {ApifoxFolder.parent_id: None}, synchronize_session=False
    )
    wipe(ApifoxFolder, ApifoxFolder.project_id == project_id)
    # 数据模型
    wipe(ApifoxSchema, ApifoxSchema.project_id == project_id)
    # 环境与变量
    wipe(ApifoxEnvironmentVarLocal, ApifoxEnvironmentVarLocal.environment_variable_id.in_(envvar_ids))
    wipe(ApifoxEnvironmentVariable, ApifoxEnvironmentVariable.environment_id.in_(env_ids))
    wipe(ApifoxEnvironmentServer, ApifoxEnvironmentServer.environment_id.in_(env_ids))
    wipe(ApifoxEnvironmentDatabase, ApifoxEnvironmentDatabase.environment_id.in_(env_ids))
    wipe(ApifoxEnvironment, ApifoxEnvironment.project_id == project_id)
    # 全局变量 / 参数
    wipe(ApifoxGlobalVarLocal, ApifoxGlobalVarLocal.global_variable_id.in_(gvar_ids))
    wipe(ApifoxGlobalVariable, ApifoxGlobalVariable.project_id == project_id)
    wipe(ApifoxGlobalParam, ApifoxGlobalParam.project_id == project_id)
    # 脚本库、调度
    wipe(ApifoxScript, ApifoxScript.project_id == project_id)
    wipe(ApifoxSchedule, ApifoxSchedule.project_id == project_id)
    # 上传文件（Binary body）
    wipe(ApifoxUploadFile, ApifoxUploadFile.project_id == project_id)


def purge_project_all(db: Session, project_id: int) -> None:
    """硬删项目前清空其**全部**数据：老平台接口自动化 + 手工执行 + 需求/用例 + apifox。

    FK 安全顺序（子表先于父表）。用批量删，不 commit（调用方 commit）。
    """
    suite_ids = select(ApiTestSuite.id).where(ApiTestSuite.project_id == project_id)
    run_ids = select(ApiTestRun.id).where(ApiTestRun.suite_id.in_(suite_ids))
    task_ids = select(ApiScheduledTask.id).where(ApiScheduledTask.project_id == project_id)
    mrun_ids = select(ManualTestRun.id).where(ManualTestRun.project_id == project_id)

    def wipe(model, cond) -> None:
        db.query(model).filter(cond).delete(synchronize_session=False)

    # 老平台接口自动化：步骤结果 → 运行 → 用例 → 定时任务链接 → 定时任务 → 套件(自引用) → 环境
    wipe(ApiTestStepResult, ApiTestStepResult.run_id.in_(run_ids))
    wipe(ApiTestRun, ApiTestRun.suite_id.in_(suite_ids))
    wipe(ApiTestCase, ApiTestCase.suite_id.in_(suite_ids))
    wipe(ApiScheduledTaskSuite, ApiScheduledTaskSuite.task_id.in_(task_ids))
    wipe(ApiScheduledTask, ApiScheduledTask.project_id == project_id)
    db.query(ApiTestSuite).filter(ApiTestSuite.project_id == project_id).update(
        {ApiTestSuite.parent_id: None}, synchronize_session=False
    )
    wipe(ApiTestSuite, ApiTestSuite.project_id == project_id)
    wipe(ApiEnvironment, ApiEnvironment.project_id == project_id)
    # 手工测试执行：明细（引用用例）→ 主表
    wipe(ManualTestRunCase, ManualTestRunCase.run_id.in_(mrun_ids))
    wipe(ManualTestRun, ManualTestRun.project_id == project_id)
    # 用例（引用需求）→ 需求
    wipe(TestCase, TestCase.project_id == project_id)
    wipe(Requirement, Requirement.project_id == project_id)
    # apifox 全套
    purge_project_apifox(db, project_id)

import { del, get, post, put, streamSSE, type Id, type SSEEvent } from './request'
import type { Schemas } from './types'

// run 流：POST 无 body，环境经 query 传，走公共 SSE 封装。
function runStream<TEvent extends SSEEvent>(
  url: string,
  environmentId: Id | undefined,
  onEvent: (event: TEvent) => void,
  options: { signal?: AbortSignal } = {},
) {
  const query = environmentId ? `?environment_id=${environmentId}` : ''
  return streamSSE<TEvent>(`${url}${query}`, { signal: options.signal, onEvent })
}

// 工作台聚合类型直接取自生成 schema（error_message / schedules / manual 均已含）
export type WorkbenchRunningPageOut = Schemas['WorkbenchRunningPageOut']
export type WorkbenchReportItem = Schemas['WorkbenchReport']
export type WorkbenchScheduleItem = Schemas['WorkbenchSchedule']
export type WorkbenchManualItem = Schemas['WorkbenchManual']
export type WorkbenchReportPageOut = Schemas['WorkbenchReportPageOut']
export type WorkbenchSchedulePageOut = Schemas['WorkbenchSchedulePageOut']
export type WorkbenchManualPageOut = Schemas['WorkbenchManualPageOut']
export type WorkbenchAiTaskItem = Schemas['WorkbenchAiTask']
export type WorkbenchAiTaskPageOut = Schemas['WorkbenchAiTaskPageOut']

export const apifoxApi = {
  workbenchOverview: () => get<Schemas['WorkbenchOverviewOut']>('/apifox/workbench/overview'),
  projectStats: (pid: Id) => get<Schemas['ProjectStatsOut']>(`/apifox/projects/${pid}/stats`),
  workbenchRunning: (params: { page?: number; page_size?: number } = {}) =>
    get<WorkbenchRunningPageOut>('/apifox/workbench/running', { params }),
  workbenchReports: (
    params: { page?: number; page_size?: number; status?: string; target_type?: string } = {},
  ) => get<WorkbenchReportPageOut>('/apifox/workbench/reports', { params }),
  workbenchFailures: (params: { page?: number; page_size?: number } = {}) =>
    get<WorkbenchReportPageOut>('/apifox/workbench/failures', { params }),
  workbenchSchedules: (params: { page?: number; page_size?: number } = {}) =>
    get<WorkbenchSchedulePageOut>('/apifox/workbench/schedules', { params }),
  workbenchManual: (params: { page?: number; page_size?: number } = {}) =>
    get<WorkbenchManualPageOut>('/apifox/workbench/manual', { params }),
  workbenchAiTasks: (params: { page?: number; page_size?: number } = {}) =>
    get<WorkbenchAiTaskPageOut>('/apifox/workbench/ai-tasks', { params }),

  listFolders: (pid: Id) => get<Schemas['FolderOut'][]>(`/apifox/projects/${pid}/folders`),
  createFolder: (pid: Id, data: Schemas['FolderCreate']) =>
    post<Schemas['FolderOut']>(`/apifox/projects/${pid}/folders`, data),
  updateFolder: (id: Id, data: Schemas['FolderUpdate']) =>
    put<Schemas['FolderOut']>(`/apifox/folders/${id}`, data),
  deleteFolder: (id: Id) => del<void>(`/apifox/folders/${id}`),
  listDefaultHeaders: () => get<Schemas['DefaultHeaderOut'][]>('/apifox/default-headers'),
  listEndpoints: (pid: Id) => get<Schemas['EndpointBrief'][]>(`/apifox/projects/${pid}/endpoints`),
  getEndpoint: (id: Id) => get<Schemas['EndpointOut']>(`/apifox/endpoints/${id}`),
  createEndpoint: (pid: Id, data: Schemas['EndpointCreate']) =>
    post<Schemas['EndpointOut']>(`/apifox/projects/${pid}/endpoints`, data),
  updateEndpoint: (id: Id, data: Schemas['EndpointUpdate']) =>
    put<Schemas['EndpointOut']>(`/apifox/endpoints/${id}`, data),
  deleteEndpoint: (id: Id) => del<void>(`/apifox/endpoints/${id}`),

  listEnvironments: (pid: Id) =>
    get<Schemas['EnvironmentOut'][]>(`/apifox/projects/${pid}/environments`),
  createEnvironment: (pid: Id, data: Schemas['EnvironmentCreate']) =>
    post<Schemas['EnvironmentOut']>(`/apifox/projects/${pid}/environments`, data),
  updateEnvironment: (id: Id, data: Schemas['EnvironmentUpdate']) =>
    put<Schemas['EnvironmentOut']>(`/apifox/environments/${id}`, data),
  deleteEnvironment: (id: Id) => del<void>(`/apifox/environments/${id}`),
  listEnvServers: (eid: Id) => get<Schemas['ServerOut'][]>(`/apifox/environments/${eid}/servers`),
  createEnvServer: (eid: Id, data: Schemas['ServerCreate']) =>
    post<Schemas['ServerOut']>(`/apifox/environments/${eid}/servers`, data),
  updateEnvServer: (sid: Id, data: Schemas['ServerUpdate']) =>
    put<Schemas['ServerOut']>(`/apifox/environment-servers/${sid}`, data),
  deleteEnvServer: (sid: Id) => del<void>(`/apifox/environment-servers/${sid}`),
  listEnvVars: (eid: Id) => get<Schemas['VariableOut'][]>(`/apifox/environments/${eid}/variables`),
  createEnvVar: (eid: Id, data: Schemas['VariableCreate']) =>
    post<Schemas['VariableOut']>(`/apifox/environments/${eid}/variables`, data),
  updateEnvVar: (vid: Id, data: Schemas['VariableUpdate']) =>
    put<Schemas['VariableOut']>(`/apifox/env-variables/${vid}`, data),
  deleteEnvVar: (vid: Id) => del<void>(`/apifox/env-variables/${vid}`),
  setEnvVarLocal: (vid: Id, local_value: Schemas['LocalValueSet']['local_value']) =>
    put<Schemas['VariableOut']>(`/apifox/env-variables/${vid}/local`, { local_value }),

  listGlobalVars: (pid: Id) =>
    get<Schemas['VariableOut'][]>(`/apifox/projects/${pid}/global-variables`),
  createGlobalVar: (pid: Id, data: Schemas['VariableCreate']) =>
    post<Schemas['VariableOut']>(`/apifox/projects/${pid}/global-variables`, data),
  updateGlobalVar: (gid: Id, data: Schemas['VariableUpdate']) =>
    put<Schemas['VariableOut']>(`/apifox/global-variables/${gid}`, data),
  deleteGlobalVar: (gid: Id) => del<void>(`/apifox/global-variables/${gid}`),
  setGlobalVarLocal: (gid: Id, local_value: Schemas['LocalValueSet']['local_value']) =>
    put<Schemas['VariableOut']>(`/apifox/global-variables/${gid}/local`, { local_value }),

  listCases: (eid: Id) => get<Schemas['CaseBrief'][]>(`/apifox/endpoints/${eid}/cases`),
  getCase: (cid: Id) => get<Schemas['CaseOut']>(`/apifox/cases/${cid}`),
  createCase: (eid: Id, data: Schemas['CaseCreate']) =>
    post<Schemas['CaseOut']>(`/apifox/endpoints/${eid}/cases`, data),
  updateCase: (cid: Id, data: Schemas['CaseUpdate']) =>
    put<Schemas['CaseOut']>(`/apifox/cases/${cid}`, data),
  deleteCase: (cid: Id) => del<void>(`/apifox/cases/${cid}`),
  batchDeleteCases: (eid: Id, caseIds: number[], opts?: { detachRefs?: boolean }) =>
    post<Schemas['CaseBatchDeleteResult']>(`/apifox/endpoints/${eid}/cases/batch-delete`, {
      case_ids: caseIds,
      detach_refs: opts?.detachRefs ?? false,
    }),
  copyCase: (cid: Id) => post<Schemas['CaseOut']>(`/apifox/cases/${cid}/copy`),
  aiGenerateCases: (eid: Id, data: Schemas['AiGenerateRequest']) =>
    post<Schemas['AiGenerateResult']>(`/apifox/endpoints/${eid}/cases/ai-generate`, data, {
      timeout: 120000, // LLM 生成耗时长，覆盖默认 60s，与功能用例生成/需求抽取一致
    }),

  // AI 生成任务化：建任务即返回，前端轮询进度（治超时/非阻塞/可恢复）
  createAiGenTask: (pid: Id, data: Schemas['AiGenTaskCreate']) =>
    post<Schemas['AiGenTaskOut']>(`/apifox/projects/${pid}/ai-gen-tasks`, data),
  getAiGenTask: (tid: Id) => get<Schemas['AiGenTaskOut']>(`/apifox/ai-gen-tasks/${tid}`),
  listActiveAiGenTasks: (pid: Id) =>
    get<Schemas['AiGenTaskBrief'][]>(`/apifox/projects/${pid}/ai-gen-tasks/active`),
  listMyActiveAiGenTasks: () =>
    get<Schemas['AiGenTaskBrief'][]>(`/apifox/ai-gen-tasks/mine/active`),
  listAiGenTasks: (
    pid: Id,
    params: {
      page?: number
      page_size?: number
      keyword?: string
      status?: string
      date_from?: string
      date_to?: string
      task_id?: number
    } = {},
  ) => get<Schemas['AiGenTaskPageOut']>(`/apifox/projects/${pid}/ai-gen-tasks`, { params }),
  cancelAiGenTask: (tid: Id) => post<Schemas['AiGenTaskOut']>(`/apifox/ai-gen-tasks/${tid}/cancel`),
  applyAiGenTaskItem: (tid: Id, iid: Id, data: Schemas['AiGenApplyRequest']) =>
    post<Schemas['AiGenApplyResult']>(`/apifox/ai-gen-tasks/${tid}/items/${iid}/apply`, data),
  applyAiGenTaskBatch: (tid: Id, data: Schemas['AiGenBatchApplyRequest']) =>
    post<Schemas['AiGenBatchApplyResult']>(`/apifox/ai-gen-tasks/${tid}/apply`, data),
  retryAiGenTaskItem: (tid: Id, iid: Id) =>
    post<Schemas['AiGenTaskOut']>(`/apifox/ai-gen-tasks/${tid}/items/${iid}/retry`),
  discardAiGenTaskItem: (tid: Id, iid: Id, data: Schemas['AiGenApplyRequest']) =>
    post<Schemas['AiGenDiscardResult']>(`/apifox/ai-gen-tasks/${tid}/items/${iid}/discard`, data),

  getNotifyConfig: (pid: Id) =>
    get<Schemas['NotifyConfigOut']>(`/apifox/projects/${pid}/notify-config`),
  updateNotifyConfig: (pid: Id, data: Schemas['NotifyConfigUpdate']) =>
    put<Schemas['NotifyConfigOut']>(`/apifox/projects/${pid}/notify-config`, data),
  testNotifyConfig: (pid: Id) =>
    post<Schemas['NotifyTestResult']>(`/apifox/projects/${pid}/notify-config/test`),

  listSchemas: (pid: Id) => get<Schemas['SchemaBrief'][]>(`/apifox/projects/${pid}/schemas`),
  getSchema: (sid: Id) => get<Schemas['SchemaOut']>(`/apifox/schemas/${sid}`),
  createSchema: (pid: Id, data: Schemas['SchemaCreate']) =>
    post<Schemas['SchemaOut']>(`/apifox/projects/${pid}/schemas`, data),
  updateSchema: (sid: Id, data: Schemas['SchemaUpdate']) =>
    put<Schemas['SchemaOut']>(`/apifox/schemas/${sid}`, data),
  deleteSchema: (sid: Id) => del<void>(`/apifox/schemas/${sid}`),

  listScripts: (pid: Id) => get<Schemas['ScriptBrief'][]>(`/apifox/projects/${pid}/scripts`),
  getScript: (sid: Id) => get<Schemas['ScriptOut']>(`/apifox/scripts/${sid}`),
  createScript: (pid: Id, data: Schemas['ScriptCreate']) =>
    post<Schemas['ScriptOut']>(`/apifox/projects/${pid}/scripts`, data),
  updateScript: (sid: Id, data: Schemas['ScriptUpdate']) =>
    put<Schemas['ScriptOut']>(`/apifox/scripts/${sid}`, data),
  deleteScript: (sid: Id) => del<void>(`/apifox/scripts/${sid}`),
  debugScript: (data: Schemas['ScriptDebugIn']) =>
    post<Schemas['ScriptDebugOut']>('/apifox/scripts/debug', data),

  listSqlScripts: (pid: Id) =>
    get<Schemas['SqlScriptBrief'][]>(`/apifox/projects/${pid}/sql-scripts`),
  getSqlScript: (sid: Id) => get<Schemas['SqlScriptOut']>(`/apifox/sql-scripts/${sid}`),
  createSqlScript: (pid: Id, data: Schemas['SqlScriptCreate']) =>
    post<Schemas['SqlScriptOut']>(`/apifox/projects/${pid}/sql-scripts`, data),
  updateSqlScript: (sid: Id, data: Schemas['SqlScriptUpdate']) =>
    put<Schemas['SqlScriptOut']>(`/apifox/sql-scripts/${sid}`, data),
  deleteSqlScript: (sid: Id) => del<void>(`/apifox/sql-scripts/${sid}`),
  debugSqlScript: (data: Schemas['SqlScriptDebugIn']) =>
    post<Schemas['SqlScriptDebugOut']>('/apifox/sql-scripts/debug', data),
  listDebugPresets: (pid: Id) =>
    get<Schemas['DebugPresetOut'][]>(`/apifox/projects/${pid}/script-debug-presets`),
  saveDebugPreset: (pid: Id, data: Schemas['DebugPresetIn']) =>
    put<Schemas['DebugPresetOut']>(`/apifox/projects/${pid}/script-debug-presets`, data),
  deleteDebugPreset: (pid: Id, presetId: Id) =>
    del<void>(`/apifox/projects/${pid}/script-debug-presets/${presetId}`),

  listGlobalParams: (pid: Id) =>
    get<Schemas['GlobalParamOut'][]>(`/apifox/projects/${pid}/global-params`),
  createGlobalParam: (pid: Id, data: Schemas['GlobalParamCreate']) =>
    post<Schemas['GlobalParamOut']>(`/apifox/projects/${pid}/global-params`, data),
  updateGlobalParam: (gid: Id, data: Schemas['GlobalParamUpdate']) =>
    put<Schemas['GlobalParamOut']>(`/apifox/global-params/${gid}`, data),
  deleteGlobalParam: (gid: Id) => del<void>(`/apifox/global-params/${gid}`),

  listProjectCases: (pid: Id) =>
    get<Schemas['ProjectCaseBrief'][]>(`/apifox/projects/${pid}/cases`),
  listScenarios: (pid: Id) => get<Schemas['ScenarioBrief'][]>(`/apifox/projects/${pid}/scenarios`),
  reorderScenarios: (pid: Id, data: Schemas['ScenarioReorderRequest']) =>
    post<Schemas['ScenarioReorderOut']>(`/apifox/projects/${pid}/scenarios/reorder`, data),
  getScenario: (sid: Id) => get<Schemas['ScenarioOut']>(`/apifox/scenarios/${sid}`),
  createScenario: (pid: Id, data: Schemas['ScenarioCreate']) =>
    post<Schemas['ScenarioOut']>(`/apifox/projects/${pid}/scenarios`, data),
  updateScenario: (sid: Id, data: Schemas['ScenarioUpdate']) =>
    put<Schemas['ScenarioOut']>(`/apifox/scenarios/${sid}`, data),
  deleteScenario: (sid: Id) => del<void>(`/apifox/scenarios/${sid}`),
  listScenarioFolders: (pid: Id) =>
    get<Schemas['ScenarioFolderOut'][]>(`/apifox/projects/${pid}/scenario-folders`),
  createScenarioFolder: (pid: Id, name: Schemas['ScenarioFolderCreate']['name']) =>
    post<Schemas['ScenarioFolderOut']>(`/apifox/projects/${pid}/scenario-folders`, { name }),
  renameScenarioFolder: (fid: Id, name: Schemas['ScenarioFolderUpdate']['name']) =>
    put<Schemas['ScenarioFolderOut']>(`/apifox/scenario-folders/${fid}`, { name }),
  deleteScenarioFolder: (fid: Id) => del<void>(`/apifox/scenario-folders/${fid}`),

  listSuites: (pid: Id) => get<Schemas['SuiteBrief'][]>(`/apifox/projects/${pid}/suites`),
  getSuite: (sid: Id) => get<Schemas['SuiteOut']>(`/apifox/suites/${sid}`),
  createSuite: (pid: Id, data: Schemas['SuiteCreate']) =>
    post<Schemas['SuiteOut']>(`/apifox/projects/${pid}/suites`, data),
  copySuite: (sid: Id) => post<Schemas['SuiteOut']>(`/apifox/suites/${sid}/copy`),
  updateSuite: (sid: Id, data: Schemas['SuiteUpdate']) =>
    put<Schemas['SuiteOut']>(`/apifox/suites/${sid}`, data),
  deleteSuite: (sid: Id) => del<void>(`/apifox/suites/${sid}`),

  uploadFile: (pid: Id, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return post<Schemas['UploadOut']>(`/apifox/projects/${pid}/uploads`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  listDatasets: (pid: Id) => get<Schemas['DatasetBrief'][]>(`/apifox/projects/${pid}/datasets`),
  getDataset: (did: Id) => get<Schemas['DatasetOut']>(`/apifox/datasets/${did}`),
  createDataset: (pid: Id, data: Schemas['DatasetCreate']) =>
    post<Schemas['DatasetOut']>(`/apifox/projects/${pid}/datasets`, data),
  updateDataset: (did: Id, data: Schemas['DatasetUpdate']) =>
    put<Schemas['DatasetOut']>(`/apifox/datasets/${did}`, data),
  deleteDataset: (did: Id) => del<void>(`/apifox/datasets/${did}`),

  listDatabases: (eid: Id) =>
    get<Schemas['DatabaseOut'][]>(`/apifox/environments/${eid}/databases`),
  createDatabase: (eid: Id, data: Schemas['DatabaseCreate']) =>
    post<Schemas['DatabaseOut']>(`/apifox/environments/${eid}/databases`, data),
  updateDatabase: (cid: Id, data: Schemas['DatabaseUpdate']) =>
    put<Schemas['DatabaseOut']>(`/apifox/env-databases/${cid}`, data),
  deleteDatabase: (cid: Id) => del<void>(`/apifox/env-databases/${cid}`),
  testDatabase: (cid: Id) =>
    post<Schemas['DatabaseTestResult']>(`/apifox/env-databases/${cid}/test`),
  testDatabaseConfig: (eid: Id, data: Schemas['DatabaseCreate']) =>
    post<Schemas['DatabaseTestResult']>(
      `/apifox/environments/${eid}/databases/test-connection`,
      data,
    ),

  importPreview: (pid: Id, data: Schemas['ImportRequest']) =>
    post<Schemas['ImportPreviewOut']>(`/apifox/projects/${pid}/import/openapi/preview`, data),
  importOpenapi: (pid: Id, data: Schemas['ImportOpenapiRequest']) =>
    post<Schemas['ImportReport']>(`/apifox/projects/${pid}/import/openapi`, data),
  importDiff: (pid: Id, data: Schemas['ImportRequest']) =>
    post<Schemas['ImportDiffOut']>(`/apifox/projects/${pid}/import/openapi/diff`, data),
  importSync: (pid: Id, data: Schemas['ImportSyncRequest']) =>
    post<Schemas['ImportSyncReport']>(`/apifox/projects/${pid}/import/openapi/sync`, data),
  getImportSource: (pid: Id) =>
    get<Schemas['ImportSourceOut']>(`/apifox/projects/${pid}/import-source`),
  exportOpenapi: (pid: Id, params: Record<string, string> = {}) =>
    get<Blob>(`/apifox/projects/${pid}/export/openapi`, { params, responseType: 'blob' }),
  exportPostman: (pid: Id, params: Record<string, string> = {}) =>
    get<Blob>(`/apifox/projects/${pid}/export/postman`, { params, responseType: 'blob' }),
  exportDoc: (pid: Id, params: Record<string, string> = {}) =>
    get<Blob>(`/apifox/projects/${pid}/export/doc`, { params, responseType: 'blob' }),

  listImportSchedules: (pid: Id) =>
    get<Schemas['ImportScheduleOut'][]>(`/apifox/projects/${pid}/import-schedules`),
  createImportSchedule: (pid: Id, data: Schemas['ImportScheduleCreate']) =>
    post<Schemas['ImportScheduleOut']>(`/apifox/projects/${pid}/import-schedules`, data),
  updateImportSchedule: (sid: Id, data: Schemas['ImportScheduleUpdate']) =>
    put<Schemas['ImportScheduleOut']>(`/apifox/import-schedules/${sid}`, data),
  deleteImportSchedule: (sid: Id) => del<void>(`/apifox/import-schedules/${sid}`),
  runImportScheduleNow: (sid: Id) =>
    post<Schemas['ImportScheduleOut']>(`/apifox/import-schedules/${sid}/run-now`),

  listApiTokens: (pid: Id) => get<Schemas['ApiTokenOut'][]>(`/apifox/projects/${pid}/api-tokens`),
  createApiToken: (pid: Id, data: Schemas['ApiTokenCreate']) =>
    post<Schemas['ApiTokenOut']>(`/apifox/projects/${pid}/api-tokens`, data),
  revokeApiToken: (tid: Id) => del<void>(`/apifox/api-tokens/${tid}`),
  reorderTree: (pid: Id, data: Schemas['TreeReorderRequest']) =>
    post<Schemas['TreeReorderOut']>(`/apifox/projects/${pid}/tree/reorder`, data),
  debugSend: (pid: Id, data: Schemas['DebugRequest']) =>
    post<Schemas['DebugResponse']>(`/apifox/projects/${pid}/debug`, data),

  listSchedules: (
    pid: Id,
    params: { keyword?: string; schedule_id?: number } = {},
  ) => get<Schemas['ScheduleOut'][]>(`/apifox/projects/${pid}/schedules`, { params }),
  createSchedule: (pid: Id, data: Schemas['ScheduleCreate']) =>
    post<Schemas['ScheduleOut']>(`/apifox/projects/${pid}/schedules`, data),
  updateSchedule: (sid: Id, data: Schemas['ScheduleUpdate']) =>
    put<Schemas['ScheduleOut']>(`/apifox/schedules/${sid}`, data),
  deleteSchedule: (sid: Id) => del<void>(`/apifox/schedules/${sid}`),
  runScheduleNow: (sid: Id) => post<Schemas['ScheduleOut']>(`/apifox/schedules/${sid}/run-now`),

  listRuns: (pid: Id) => get<Schemas['RunBrief'][]>(`/apifox/projects/${pid}/runs`),
  listRunsPage: (
    pid: Id,
    params: {
      page?: number
      page_size?: number
      target_types?: string
      keyword?: string
      run_id?: number
      status?: string
      date_from?: string
      date_to?: string
    } = {},
  ) => get<Schemas['RunPageOut']>(`/apifox/projects/${pid}/runs/page`, { params }),
  listEndpointRuns: (eid: Id) => get<Schemas['RunBrief'][]>(`/apifox/endpoints/${eid}/runs`),
  getRun: (rid: Id) => get<Schemas['RunOut']>(`/apifox/runs/${rid}`),
  deleteRun: (rid: Id) => del<void>(`/apifox/runs/${rid}`),
  batchDeleteRuns: (pid: Id, runIds: Id[]) =>
    post<{ succeeded: number; failed: number; errors: string[] }>(
      `/apifox/projects/${pid}/runs/batch-delete`,
      { run_ids: runIds },
    ),
  exportRun: (rid: Id, format = 'excel') =>
    get<Blob>(`/apifox/runs/${rid}/export`, { params: { format }, responseType: 'blob' }),
  runCaseStream: <TEvent extends SSEEvent>(
    cid: Id,
    environmentId: Id | undefined,
    onEvent: (event: TEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) => runStream(`/api/v1/apifox/cases/${cid}/run/stream`, environmentId, onEvent, options),
  runScenarioStream: <TEvent extends SSEEvent>(
    sid: Id,
    environmentId: Id | undefined,
    onEvent: (event: TEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) => runStream(`/api/v1/apifox/scenarios/${sid}/run/stream`, environmentId, onEvent, options),
  runSuiteStream: <TEvent extends SSEEvent>(
    sid: Id,
    environmentId: Id | undefined,
    onEvent: (event: TEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) => runStream(`/api/v1/apifox/suites/${sid}/run/stream`, environmentId, onEvent, options),
  runEndpointAllStream: <TEvent extends SSEEvent>(
    eid: Id,
    environmentId: Id | undefined,
    caseIds: Id[],
    onEvent: (event: TEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) => {
    const query = environmentId ? `?environment_id=${environmentId}` : ''
    return streamSSE<TEvent>(`/api/v1/apifox/endpoints/${eid}/cases/run-all/stream${query}`, {
      signal: options.signal,
      onEvent,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_ids: caseIds }),
    })
  },

  // 回收站（软删除的场景/套件/用例）
  listTrash: (
    pid: Id,
    params?: {
      page?: number
      page_size?: number
      keyword?: string
      kind?: Schemas['TrashItem']['kind']
    },
  ) => get<Schemas['TrashPageOut']>(`/apifox/projects/${pid}/trash`, { params }),
  restoreTrash: (kind: Schemas['TrashItem']['kind'], id: Id) =>
    post<Schemas['TrashRestoreOut']>(`/apifox/trash/${kind}/${id}/restore`),
  purgeTrash: (kind: Schemas['TrashItem']['kind'], id: Id) =>
    del<void>(`/apifox/trash/${kind}/${id}`),
  batchRestoreTrash: (pid: Id, items: { kind: Schemas['TrashItem']['kind']; id: Id }[]) =>
    post<{ succeeded: number; failed: number; errors: string[] }>(
      `/apifox/projects/${pid}/trash/batch-restore`,
      { items },
    ),
  batchPurgeTrash: (pid: Id, items: { kind: Schemas['TrashItem']['kind']; id: Id }[]) =>
    post<{ succeeded: number; failed: number; errors: string[] }>(
      `/apifox/projects/${pid}/trash/batch-purge`,
      { items },
    ),
}

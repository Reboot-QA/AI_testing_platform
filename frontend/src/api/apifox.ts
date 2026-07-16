import { del, get, post, put, streamSSE, type Id, type SSEEvent } from './request'
import type { Schemas } from './types'

// run 流：POST 无 body，环境经 query 传，走公共 SSE 封装。
function runStream(
  url: string,
  environmentId: Id | undefined,
  onEvent: (event: SSEEvent) => void,
  options: { signal?: AbortSignal } = {},
) {
  const query = environmentId ? `?environment_id=${environmentId}` : ''
  return streamSSE(`${url}${query}`, { signal: options.signal, onEvent })
}

export const apifoxApi = {
  workbenchOverview: () => get<Schemas['WorkbenchOverviewOut']>('/apifox/workbench/overview'),

  listFolders: (pid: Id) => get<Schemas['FolderOut'][]>(`/apifox/projects/${pid}/folders`),
  createFolder: (pid: Id, data: Schemas['FolderCreate']) =>
    post<Schemas['FolderOut']>(`/apifox/projects/${pid}/folders`, data),
  updateFolder: (id: Id, data: Schemas['FolderUpdate']) =>
    put<Schemas['FolderOut']>(`/apifox/folders/${id}`, data),
  deleteFolder: (id: Id) => del<any>(`/apifox/folders/${id}`),
  listEndpoints: (pid: Id) => get<Schemas['EndpointBrief'][]>(`/apifox/projects/${pid}/endpoints`),
  getEndpoint: (id: Id) => get<Schemas['EndpointOut']>(`/apifox/endpoints/${id}`),
  createEndpoint: (pid: Id, data: Schemas['EndpointCreate']) =>
    post<Schemas['EndpointOut']>(`/apifox/projects/${pid}/endpoints`, data),
  updateEndpoint: (id: Id, data: Schemas['EndpointUpdate']) =>
    put<Schemas['EndpointOut']>(`/apifox/endpoints/${id}`, data),
  deleteEndpoint: (id: Id) => del<any>(`/apifox/endpoints/${id}`),

  listEnvironments: (pid: Id) =>
    get<Schemas['EnvironmentOut'][]>(`/apifox/projects/${pid}/environments`),
  createEnvironment: (pid: Id, data: Schemas['EnvironmentCreate']) =>
    post<Schemas['EnvironmentOut']>(`/apifox/projects/${pid}/environments`, data),
  updateEnvironment: (id: Id, data: Schemas['EnvironmentUpdate']) =>
    put<Schemas['EnvironmentOut']>(`/apifox/environments/${id}`, data),
  deleteEnvironment: (id: Id) => del<any>(`/apifox/environments/${id}`),
  listEnvServers: (eid: Id) => get<Schemas['ServerOut'][]>(`/apifox/environments/${eid}/servers`),
  createEnvServer: (eid: Id, data: Schemas['ServerCreate']) =>
    post<Schemas['ServerOut']>(`/apifox/environments/${eid}/servers`, data),
  updateEnvServer: (sid: Id, data: Schemas['ServerUpdate']) =>
    put<Schemas['ServerOut']>(`/apifox/environment-servers/${sid}`, data),
  deleteEnvServer: (sid: Id) => del<any>(`/apifox/environment-servers/${sid}`),
  listEnvVars: (eid: Id) => get<Schemas['VariableOut'][]>(`/apifox/environments/${eid}/variables`),
  createEnvVar: (eid: Id, data: Schemas['VariableCreate']) =>
    post<Schemas['VariableOut']>(`/apifox/environments/${eid}/variables`, data),
  updateEnvVar: (vid: Id, data: Schemas['VariableUpdate']) =>
    put<Schemas['VariableOut']>(`/apifox/env-variables/${vid}`, data),
  deleteEnvVar: (vid: Id) => del<any>(`/apifox/env-variables/${vid}`),
  setEnvVarLocal: (vid: Id, local_value: Schemas['LocalValueSet']['local_value']) =>
    put<Schemas['VariableOut']>(`/apifox/env-variables/${vid}/local`, { local_value }),

  listGlobalVars: (pid: Id) =>
    get<Schemas['VariableOut'][]>(`/apifox/projects/${pid}/global-variables`),
  createGlobalVar: (pid: Id, data: Schemas['VariableCreate']) =>
    post<Schemas['VariableOut']>(`/apifox/projects/${pid}/global-variables`, data),
  updateGlobalVar: (gid: Id, data: Schemas['VariableUpdate']) =>
    put<Schemas['VariableOut']>(`/apifox/global-variables/${gid}`, data),
  deleteGlobalVar: (gid: Id) => del<any>(`/apifox/global-variables/${gid}`),
  setGlobalVarLocal: (gid: Id, local_value: Schemas['LocalValueSet']['local_value']) =>
    put<Schemas['VariableOut']>(`/apifox/global-variables/${gid}/local`, { local_value }),

  listCases: (eid: Id) => get<Schemas['CaseBrief'][]>(`/apifox/endpoints/${eid}/cases`),
  getCase: (cid: Id) => get<Schemas['CaseOut']>(`/apifox/cases/${cid}`),
  createCase: (eid: Id, data: Schemas['CaseCreate']) =>
    post<Schemas['CaseOut']>(`/apifox/endpoints/${eid}/cases`, data),
  updateCase: (cid: Id, data: Schemas['CaseUpdate']) =>
    put<Schemas['CaseOut']>(`/apifox/cases/${cid}`, data),
  deleteCase: (cid: Id) => del<any>(`/apifox/cases/${cid}`),
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
  cancelAiGenTask: (tid: Id) => post<Schemas['AiGenTaskOut']>(`/apifox/ai-gen-tasks/${tid}/cancel`),
  applyAiGenTaskItem: (tid: Id, iid: Id, data: Schemas['AiGenApplyRequest']) =>
    post<Schemas['AiGenApplyResult']>(`/apifox/ai-gen-tasks/${tid}/items/${iid}/apply`, data),

  listSchemas: (pid: Id) => get<Schemas['SchemaBrief'][]>(`/apifox/projects/${pid}/schemas`),
  getSchema: (sid: Id) => get<Schemas['SchemaOut']>(`/apifox/schemas/${sid}`),
  createSchema: (pid: Id, data: Schemas['SchemaCreate']) =>
    post<Schemas['SchemaOut']>(`/apifox/projects/${pid}/schemas`, data),
  updateSchema: (sid: Id, data: Schemas['SchemaUpdate']) =>
    put<Schemas['SchemaOut']>(`/apifox/schemas/${sid}`, data),
  deleteSchema: (sid: Id) => del<any>(`/apifox/schemas/${sid}`),

  listScripts: (pid: Id) => get<Schemas['ScriptBrief'][]>(`/apifox/projects/${pid}/scripts`),
  getScript: (sid: Id) => get<Schemas['ScriptOut']>(`/apifox/scripts/${sid}`),
  createScript: (pid: Id, data: Schemas['ScriptCreate']) =>
    post<Schemas['ScriptOut']>(`/apifox/projects/${pid}/scripts`, data),
  updateScript: (sid: Id, data: Schemas['ScriptUpdate']) =>
    put<Schemas['ScriptOut']>(`/apifox/scripts/${sid}`, data),
  deleteScript: (sid: Id) => del<any>(`/apifox/scripts/${sid}`),
  debugScript: (data: Schemas['ScriptDebugIn']) =>
    post<Schemas['ScriptDebugOut']>('/apifox/scripts/debug', data),

  listGlobalParams: (pid: Id) =>
    get<Schemas['GlobalParamOut'][]>(`/apifox/projects/${pid}/global-params`),
  createGlobalParam: (pid: Id, data: Schemas['GlobalParamCreate']) =>
    post<Schemas['GlobalParamOut']>(`/apifox/projects/${pid}/global-params`, data),
  updateGlobalParam: (gid: Id, data: Schemas['GlobalParamUpdate']) =>
    put<Schemas['GlobalParamOut']>(`/apifox/global-params/${gid}`, data),
  deleteGlobalParam: (gid: Id) => del<any>(`/apifox/global-params/${gid}`),

  listProjectCases: (pid: Id) =>
    get<Schemas['ProjectCaseBrief'][]>(`/apifox/projects/${pid}/cases`),
  listScenarios: (pid: Id) => get<Schemas['ScenarioBrief'][]>(`/apifox/projects/${pid}/scenarios`),
  getScenario: (sid: Id) => get<Schemas['ScenarioOut']>(`/apifox/scenarios/${sid}`),
  createScenario: (pid: Id, data: Schemas['ScenarioCreate']) =>
    post<Schemas['ScenarioOut']>(`/apifox/projects/${pid}/scenarios`, data),
  updateScenario: (sid: Id, data: Schemas['ScenarioUpdate']) =>
    put<Schemas['ScenarioOut']>(`/apifox/scenarios/${sid}`, data),
  deleteScenario: (sid: Id) => del<any>(`/apifox/scenarios/${sid}`),
  listScenarioFolders: (pid: Id) =>
    get<Schemas['ScenarioFolderOut'][]>(`/apifox/projects/${pid}/scenario-folders`),
  createScenarioFolder: (pid: Id, name: Schemas['ScenarioFolderCreate']['name']) =>
    post<Schemas['ScenarioFolderOut']>(`/apifox/projects/${pid}/scenario-folders`, { name }),
  renameScenarioFolder: (fid: Id, name: Schemas['ScenarioFolderUpdate']['name']) =>
    put<Schemas['ScenarioFolderOut']>(`/apifox/scenario-folders/${fid}`, { name }),
  deleteScenarioFolder: (fid: Id) => del<any>(`/apifox/scenario-folders/${fid}`),

  listSuites: (pid: Id) => get<Schemas['SuiteBrief'][]>(`/apifox/projects/${pid}/suites`),
  getSuite: (sid: Id) => get<Schemas['SuiteOut']>(`/apifox/suites/${sid}`),
  createSuite: (pid: Id, data: Schemas['SuiteCreate']) =>
    post<Schemas['SuiteOut']>(`/apifox/projects/${pid}/suites`, data),
  copySuite: (sid: Id) => post<Schemas['SuiteOut']>(`/apifox/suites/${sid}/copy`),
  updateSuite: (sid: Id, data: Schemas['SuiteUpdate']) =>
    put<Schemas['SuiteOut']>(`/apifox/suites/${sid}`, data),
  deleteSuite: (sid: Id) => del<any>(`/apifox/suites/${sid}`),

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
  deleteDataset: (did: Id) => del<any>(`/apifox/datasets/${did}`),

  listDatabases: (eid: Id) =>
    get<Schemas['DatabaseOut'][]>(`/apifox/environments/${eid}/databases`),
  createDatabase: (eid: Id, data: Schemas['DatabaseCreate']) =>
    post<Schemas['DatabaseOut']>(`/apifox/environments/${eid}/databases`, data),
  updateDatabase: (cid: Id, data: Schemas['DatabaseUpdate']) =>
    put<Schemas['DatabaseOut']>(`/apifox/env-databases/${cid}`, data),
  deleteDatabase: (cid: Id) => del<any>(`/apifox/env-databases/${cid}`),
  testDatabase: (cid: Id) => post<any>(`/apifox/env-databases/${cid}/test`), // 无 response_model（技术债）

  importOpenapi: (pid: Id, data: Schemas['ImportRequest']) =>
    post<Schemas['ImportReport']>(`/apifox/projects/${pid}/import/openapi`, data),
  importDiff: (pid: Id, data: Schemas['ImportRequest']) =>
    post<Schemas['ImportDiffOut']>(`/apifox/projects/${pid}/import/openapi/diff`, data),
  importSync: (pid: Id, data: Schemas['ImportSyncRequest']) =>
    post<Schemas['ImportSyncReport']>(`/apifox/projects/${pid}/import/openapi/sync`, data),
  reorderTree: (pid: Id, data: Schemas['TreeReorderRequest']) =>
    post<any>(`/apifox/projects/${pid}/tree/reorder`, data), // 无 response_model（技术债）
  debugSend: (pid: Id, data: Schemas['DebugRequest']) =>
    post<Schemas['DebugResponse']>(`/apifox/projects/${pid}/debug`, data),

  listSchedules: (pid: Id) => get<Schemas['ScheduleOut'][]>(`/apifox/projects/${pid}/schedules`),
  createSchedule: (pid: Id, data: Schemas['ScheduleCreate']) =>
    post<Schemas['ScheduleOut']>(`/apifox/projects/${pid}/schedules`, data),
  updateSchedule: (sid: Id, data: Schemas['ScheduleUpdate']) =>
    put<Schemas['ScheduleOut']>(`/apifox/schedules/${sid}`, data),
  deleteSchedule: (sid: Id) => del<any>(`/apifox/schedules/${sid}`),
  runScheduleNow: (sid: Id) => post<Schemas['ScheduleOut']>(`/apifox/schedules/${sid}/run-now`),

  listRuns: (pid: Id) => get<Schemas['RunBrief'][]>(`/apifox/projects/${pid}/runs`),
  listEndpointRuns: (eid: Id) => get<Schemas['RunBrief'][]>(`/apifox/endpoints/${eid}/runs`),
  getRun: (rid: Id) => get<Schemas['RunOut']>(`/apifox/runs/${rid}`),
  exportRun: (rid: Id, format = 'excel') =>
    get<Blob>(`/apifox/runs/${rid}/export`, { params: { format }, responseType: 'blob' }),
  runCaseStream: (
    cid: Id,
    environmentId: Id | undefined,
    onEvent: (event: SSEEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) => runStream(`/api/v1/apifox/cases/${cid}/run/stream`, environmentId, onEvent, options),
  runScenarioStream: (
    sid: Id,
    environmentId: Id | undefined,
    onEvent: (event: SSEEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) => runStream(`/api/v1/apifox/scenarios/${sid}/run/stream`, environmentId, onEvent, options),
  runSuiteStream: (
    sid: Id,
    environmentId: Id | undefined,
    onEvent: (event: SSEEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) => runStream(`/api/v1/apifox/suites/${sid}/run/stream`, environmentId, onEvent, options),
}

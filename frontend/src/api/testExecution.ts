import { del, get, post, put, type Id } from './request'
import type { Schemas } from './types'

export const testExecutionApi = {
  listRuns: (projectId: Id) =>
    get<Schemas['ManualTestRunSummaryOut'][]>('/test-executions', {
      params: { project_id: projectId },
    }),
  getRun: (id: Id) => get<Schemas['ManualTestRunDetailOut']>(`/test-executions/${id}`),
  createRun: (data: Schemas['ManualTestRunCreate']) =>
    post<Schemas['ManualTestRunDetailOut']>('/test-executions', data),
  updateRun: (id: Id, data: Schemas['ManualTestRunUpdate']) =>
    put<Schemas['ManualTestRunSummaryOut']>(`/test-executions/${id}`, data),
  deleteRun: (id: Id) => del<any>(`/test-executions/${id}`), // 无 response_model（技术债）
  submitCaseResult: (runId: Id, caseRowId: Id, data: Schemas['ManualTestRunCaseResultUpdate']) =>
    put<Schemas['ManualTestRunCaseOut']>(`/test-executions/${runId}/cases/${caseRowId}`, data),
  // 无 response_model（可选用例列表返回自由结构）：any 占位（技术债）
  listAvailableCases: (projectId: Id, params: Record<string, unknown> = {}) =>
    get<any>('/test-executions/available-cases/list', {
      params: { project_id: projectId, ...params },
      paramsSerializer: { indexes: null },
    }),
}

import { del, get, post, put, type Id } from './request'
import type { Schemas } from './types'

export const testExecutionApi = {
  listRuns: (projectId: Id) =>
    get<Schemas['ManualTestRunSummaryOut'][]>('/test-executions', {
      params: { project_id: projectId },
    }),
  listRunsPage: (
    projectId: Id,
    params?: {
      page?: number
      page_size?: number
      status?: string
      keyword?: string
      date_from?: string
      date_to?: string
    },
  ) =>
    get<Schemas['ManualTestRunPageOut']>('/test-executions/page', {
      params: { project_id: projectId, ...params },
    }),
  getRun: (id: Id) => get<Schemas['ManualTestRunDetailOut']>(`/test-executions/${id}`),
  createRun: (data: Schemas['ManualTestRunCreate']) =>
    post<Schemas['ManualTestRunDetailOut']>('/test-executions', data),
  updateRun: (id: Id, data: Schemas['ManualTestRunUpdate']) =>
    put<Schemas['ManualTestRunSummaryOut']>(`/test-executions/${id}`, data),
  deleteRun: (id: Id) => del<void>(`/test-executions/${id}`),
  batchDeleteRuns: (data: Schemas['ManualTestRunBatchDelete']) =>
    post<Schemas['BatchDeleteResponse']>('/test-executions/batch/delete', data),
  submitCaseResult: (runId: Id, caseRowId: Id, data: Schemas['ManualTestRunCaseResultUpdate']) =>
    put<Schemas['ManualTestRunCaseOut']>(`/test-executions/${runId}/cases/${caseRowId}`, data),
  listAvailableCases: (projectId: Id, params: Record<string, unknown> = {}) =>
    get<Schemas['ManualTestRunAvailableCaseOut'][]>('/test-executions/available-cases/list', {
      params: { project_id: projectId, ...params },
      paramsSerializer: { indexes: null },
    }),
  exportRun: (runId: Id, format = 'excel') =>
    get<Blob>(`/test-executions/${runId}/export`, { params: { format }, responseType: 'blob' }),
}

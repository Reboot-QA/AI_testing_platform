import { del, get, post, put, streamSSE, type Id, type SSEEvent } from './request'
import type { Schemas } from './types'

export const testcaseApi = {
  // 无 response_model（列表返回自由结构）：any 占位（技术债）
  list: (params?: Record<string, unknown>) => get<any>('/testcases', { params }),
  create: (data: Schemas['TestCaseCreate']) => post<Schemas['TestCaseOut']>('/testcases', data),
  update: (id: Id, data: Schemas['TestCaseUpdate']) =>
    put<Schemas['TestCaseOut']>(`/testcases/${id}`, data),
  delete: (id: Id) => del<any>(`/testcases/${id}`), // 无 response_model（技术债）
  batchDelete: (data: Schemas['TestCaseBatchDelete']) =>
    post<Schemas['BatchDeleteResponse']>('/testcases/batch/delete', data),
  batchReview: (data: Schemas['TestCaseBatchReviewUpdate']) =>
    post<Schemas['TestCaseBatchReviewResponse']>('/testcases/batch/review', data),
  aiGenerate: (data: Schemas['AIGenerateRequest']) =>
    post<Schemas['AIGenerateResponse']>('/testcases/ai/generate', data, { timeout: 120000 }),
  aiGenerateStream: (
    data: Schemas['AIGenerateRequest'],
    onEvent: (event: SSEEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) =>
    streamSSE('/api/v1/testcases/ai/generate/stream', {
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' },
      signal: options.signal,
      onEvent,
    }),
  exportExcel: (projectId: Id) =>
    get<Blob>('/testcases/export/excel', {
      params: { project_id: projectId },
      responseType: 'blob',
    }),
  exportXmind: (projectId: Id) =>
    get<Blob>('/testcases/export/xmind', {
      params: { project_id: projectId },
      responseType: 'blob',
    }),
  importFile: (projectId: Id, file: File) => {
    const form = new FormData()
    form.append('project_id', String(projectId))
    form.append('file', file)
    return post<Schemas['TestCaseFileImportResponse']>('/testcases/import/file', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },
}

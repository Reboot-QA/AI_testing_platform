import { del, get, post, put, streamSSE, type Id, type SSEEvent } from './request'
import type { Schemas } from './types'

export const testcaseApi = {
  list: (params?: Record<string, unknown>) =>
    get<Schemas['TestCaseOut'][]>('/testcases', { params }),
  listPage: (params: Record<string, unknown> & { page: number; page_size: number }) =>
    get<Schemas['TestCasePageOut']>('/testcases', { params }),
  create: (data: Schemas['TestCaseCreate']) => post<Schemas['TestCaseOut']>('/testcases', data),
  update: (id: Id, data: Schemas['TestCaseUpdate']) =>
    put<Schemas['TestCaseOut']>(`/testcases/${id}`, data),
  delete: (id: Id) => del<void>(`/testcases/${id}`),
  batchDelete: (data: Schemas['TestCaseBatchDelete']) =>
    post<Schemas['BatchDeleteResponse']>('/testcases/batch/delete', data),
  batchReview: (data: Schemas['TestCaseBatchReviewUpdate']) =>
    post<Schemas['TestCaseBatchReviewResponse']>('/testcases/batch/review', data),
  aiGenerate: (data: Schemas['AIGenerateRequest']) =>
    post<Schemas['AIGenerateResponse']>('/testcases/ai/generate', data, { timeout: 120000 }),
  aiGenerateStream: <TEvent extends SSEEvent>(
    data: Schemas['AIGenerateRequest'],
    onEvent: (event: TEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) =>
    streamSSE<TEvent>('/api/v1/testcases/ai/generate/stream', {
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
  importFile: (projectId: Id, file: File, importMode: 'append' | 'replace' = 'append') => {
    const form = new FormData()
    form.append('project_id', String(projectId))
    form.append('import_mode', importMode)
    form.append('file', file)
    return post<Schemas['TestCaseFileImportResponse']>('/testcases/import/file', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },
  downloadImportTemplateExcel: () =>
    get<Blob>('/testcases/import/template/excel', { responseType: 'blob' }),
  downloadImportTemplateXmind: () =>
    get<Blob>('/testcases/import/template/xmind', { responseType: 'blob' }),
}

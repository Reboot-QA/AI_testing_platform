import { del, get, post, put, streamSSE, type Id, type SSEEvent } from './request'
import type { Schemas } from './types'

export const requirementApi = {
  // 无 response_model（列表返回自由结构）：any 占位（技术债）
  list: (projectId?: Id, params: Record<string, unknown> = {}) => {
    const queryParams = { ...params }
    if (projectId != null) queryParams.project_id = projectId
    return get<any>('/requirements', { params: queryParams })
  },
  create: (data: Schemas['RequirementCreate']) =>
    post<Schemas['RequirementOut']>('/requirements', data),
  update: (id: Id, data: Schemas['RequirementUpdate']) =>
    put<Schemas['RequirementOut']>(`/requirements/${id}`, data),
  delete: (id: Id) => del<any>(`/requirements/${id}`), // 无 response_model（技术债）
  clearTestcases: (id: Id) => del<any>(`/requirements/${id}/testcases`), // 无 response_model（技术债）
  batchUpdateStatus: (data: Schemas['RequirementBatchStatusUpdate']) =>
    post<Schemas['RequirementBatchStatusResponse']>('/requirements/batch/status', data),
  batchDelete: (data: Schemas['RequirementBatchDelete']) =>
    post<Schemas['RequirementBatchDeleteResponse']>('/requirements/batch/delete', data),
  extractFromDocument: (projectId: Id, file: File, providerId?: Id) => {
    const form = new FormData()
    form.append('project_id', String(projectId))
    form.append('file', file)
    if (providerId) form.append('provider_id', String(providerId))
    return post<Schemas['RequirementExtractResponse']>('/requirements/ai/extract', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },
  extractFromDocumentStream: (
    projectId: Id,
    file: File,
    providerId: Id | undefined,
    onEvent: (event: SSEEvent) => void,
  ) => {
    const form = new FormData()
    form.append('project_id', String(projectId))
    form.append('file', file)
    if (providerId) form.append('provider_id', String(providerId))
    // multipart：不设 Content-Type，交由浏览器带 boundary
    return streamSSE('/api/v1/requirements/ai/extract/stream', { body: form, onEvent })
  },
  batchImport: (data: Schemas['RequirementBatchImport']) =>
    post<Schemas['RequirementBatchImportResponse']>('/requirements/batch/import', data),
  exportExcel: (projectId: Id) =>
    get<Blob>('/requirements/export/excel', {
      params: { project_id: projectId },
      responseType: 'blob',
    }),
  exportXmind: (projectId: Id) =>
    get<Blob>('/requirements/export/xmind', {
      params: { project_id: projectId },
      responseType: 'blob',
    }),
  importFile: (projectId: Id, file: File) => {
    const form = new FormData()
    form.append('project_id', String(projectId))
    form.append('file', file)
    return post<Schemas['RequirementFileImportResponse']>('/requirements/import/file', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },
}

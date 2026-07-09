import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    if (error.response?.status === 401) {
      const isGrafanaProxy = error.config?.url?.includes('/logs/grafana')
      if (!isGrafanaProxy) {
        localStorage.removeItem('token')
        if (!window.location.pathname.includes('/login')) {
          window.location.href = '/login'
        }
      }
    }
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (username, password) => {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    return request.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  register: (data) => request.post('/auth/register', data),
  me: () => request.get('/auth/me'),
  changePassword: (data) => request.put('/auth/password', data),
}

export const projectApi = {
  list: () => request.get('/projects'),
  get: (id) => request.get(`/projects/${id}`),
  create: (data) => request.post('/projects', data),
  update: (id, data) => request.put(`/projects/${id}`, data),
  delete: (id) => request.delete(`/projects/${id}`),
  dashboard: () => request.get('/projects/stats/dashboard'),
}

export const requirementApi = {
  list: (projectId, params = {}) =>
    request.get('/requirements', { params: { project_id: projectId, ...params } }),
  create: (data) => request.post('/requirements', data),
  update: (id, data) => request.put(`/requirements/${id}`, data),
  delete: (id) => request.delete(`/requirements/${id}`),
  clearTestcases: (id) => request.delete(`/requirements/${id}/testcases`),
  batchUpdateStatus: (data) => request.post('/requirements/batch/status', data),
  batchDelete: (data) => request.post('/requirements/batch/delete', data),
  extractFromDocument: (projectId, file, providerId) => {
    const form = new FormData()
    form.append('project_id', projectId)
    form.append('file', file)
    if (providerId) form.append('provider_id', providerId)
    return request.post('/requirements/ai/extract', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },
  extractFromDocumentStream: (projectId, file, providerId, onEvent) => {
    const form = new FormData()
    form.append('project_id', projectId)
    form.append('file', file)
    if (providerId) form.append('provider_id', providerId)
    const token = localStorage.getItem('token')
    return fetch('/api/v1/requirements/ai/extract/stream', {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: form,
    }).then(async (response) => {
      if (!response.ok) {
        let message = '请求失败'
        try {
          const body = await response.json()
          message = body.detail || message
        } catch {
          // ignore parse error
        }
        throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''
        for (const chunk of chunks) {
          const line = chunk.trim()
          if (!line.startsWith('data:')) continue
          const event = JSON.parse(line.slice(5).trim())
          onEvent(event)
        }
      }
    })
  },
  batchImport: (data) => request.post('/requirements/batch/import', data),
}

export const testcaseApi = {
  list: (params) => request.get('/testcases', { params }),
  create: (data) => request.post('/testcases', data),
  update: (id, data) => request.put(`/testcases/${id}`, data),
  delete: (id) => request.delete(`/testcases/${id}`),
  batchDelete: (data) => request.post('/testcases/batch/delete', data),
  batchReview: (data) => request.post('/testcases/batch/review', data),
  aiGenerate: (data) => request.post('/testcases/ai/generate', data, { timeout: 120000 }),
  aiGenerateStream: (data, onEvent, options = {}) => {
    const token = localStorage.getItem('token')
    return fetch('/api/v1/testcases/ai/generate/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
      signal: options.signal,
    }).then(async (response) => {
      if (!response.ok) {
        let message = '请求失败'
        try {
          const body = await response.json()
          message = body.detail || message
        } catch {
          // ignore parse error
        }
        throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''
        for (const chunk of chunks) {
          const line = chunk.trim()
          if (!line.startsWith('data:')) continue
          const event = JSON.parse(line.slice(5).trim())
          onEvent(event)
        }
      }
    })
  },
  exportExcel: (projectId) =>
    request.get('/testcases/export/excel', {
      params: { project_id: projectId },
      responseType: 'blob',
    }),
}

export const settingsApi = {
  getLLM: () => request.get('/settings/llm'),
  getLLMOptions: () => request.get('/settings/llm/options'),
  updateMockMode: (mock_mode) => request.put('/settings/llm/mock', { mock_mode }),
  createProvider: (data) => request.post('/settings/llm/providers', data),
  updateProvider: (id, data) => request.put(`/settings/llm/providers/${id}`, data),
  deleteProvider: (id) => request.delete(`/settings/llm/providers/${id}`),
  activateProvider: (id) => request.put(`/settings/llm/providers/${id}/activate`),
  testLLM: (data) => request.post('/settings/llm/test', data || {}),
}

export const assistantApi = {
  chatStream: (data, onEvent, options = {}) => {
    const token = localStorage.getItem('token')
    return fetch('/api/v1/assistant/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(data),
      signal: options.signal,
    }).then(async (response) => {
      if (!response.ok) {
        let message = '请求失败'
        try {
          const body = await response.json()
          message = body.detail || message
        } catch {
          // ignore
        }
        throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''
        for (const chunk of chunks) {
          const line = chunk.trim()
          if (!line.startsWith('data:')) continue
          onEvent(JSON.parse(line.slice(5).trim()))
        }
      }
    })
  },
}

export const departmentApi = {
  list: () => request.get('/departments'),
  create: (data) => request.post('/departments', data),
  update: (id, data) => request.put(`/departments/${id}`, data),
  delete: (id) => request.delete(`/departments/${id}`),
}

export const userApi = {
  list: () => request.get('/users'),
  create: (data) => request.post('/users', data),
  update: (id, data) => request.put(`/users/${id}`, data),
  resetPassword: (id, password) => request.put(`/users/${id}/password`, { password }),
  delete: (id) => request.delete(`/users/${id}`),
  listMenus: () => request.get('/users/menus'),
  getPermissions: (id) => request.get(`/users/${id}/permissions`),
  updatePermissions: (id, menu_permissions) =>
    request.put(`/users/${id}/permissions`, { menu_permissions }),
}

export const apifoxApi = {
  listFolders: (pid) => request.get(`/apifox/projects/${pid}/folders`),
  createFolder: (pid, data) => request.post(`/apifox/projects/${pid}/folders`, data),
  updateFolder: (id, data) => request.put(`/apifox/folders/${id}`, data),
  deleteFolder: (id) => request.delete(`/apifox/folders/${id}`),
  listEndpoints: (pid) => request.get(`/apifox/projects/${pid}/endpoints`),
  getEndpoint: (id) => request.get(`/apifox/endpoints/${id}`),
  createEndpoint: (pid, data) => request.post(`/apifox/projects/${pid}/endpoints`, data),
  updateEndpoint: (id, data) => request.put(`/apifox/endpoints/${id}`, data),
  deleteEndpoint: (id) => request.delete(`/apifox/endpoints/${id}`),

  listEnvironments: (pid) => request.get(`/apifox/projects/${pid}/environments`),
  createEnvironment: (pid, data) => request.post(`/apifox/projects/${pid}/environments`, data),
  updateEnvironment: (id, data) => request.put(`/apifox/environments/${id}`, data),
  deleteEnvironment: (id) => request.delete(`/apifox/environments/${id}`),
  listEnvVars: (eid) => request.get(`/apifox/environments/${eid}/variables`),
  createEnvVar: (eid, data) => request.post(`/apifox/environments/${eid}/variables`, data),
  updateEnvVar: (vid, data) => request.put(`/apifox/env-variables/${vid}`, data),
  deleteEnvVar: (vid) => request.delete(`/apifox/env-variables/${vid}`),
  setEnvVarLocal: (vid, local_value) => request.put(`/apifox/env-variables/${vid}/local`, { local_value }),

  listGlobalVars: (pid) => request.get(`/apifox/projects/${pid}/global-variables`),
  createGlobalVar: (pid, data) => request.post(`/apifox/projects/${pid}/global-variables`, data),
  updateGlobalVar: (gid, data) => request.put(`/apifox/global-variables/${gid}`, data),
  deleteGlobalVar: (gid) => request.delete(`/apifox/global-variables/${gid}`),
  setGlobalVarLocal: (gid, local_value) => request.put(`/apifox/global-variables/${gid}/local`, { local_value }),

  listCases: (eid) => request.get(`/apifox/endpoints/${eid}/cases`),
  getCase: (cid) => request.get(`/apifox/cases/${cid}`),
  createCase: (eid, data) => request.post(`/apifox/endpoints/${eid}/cases`, data),
  updateCase: (cid, data) => request.put(`/apifox/cases/${cid}`, data),
  deleteCase: (cid) => request.delete(`/apifox/cases/${cid}`),

  listSchemas: (pid) => request.get(`/apifox/projects/${pid}/schemas`),
  getSchema: (sid) => request.get(`/apifox/schemas/${sid}`),
  createSchema: (pid, data) => request.post(`/apifox/projects/${pid}/schemas`, data),
  updateSchema: (sid, data) => request.put(`/apifox/schemas/${sid}`, data),
  deleteSchema: (sid) => request.delete(`/apifox/schemas/${sid}`),

  listScripts: (pid) => request.get(`/apifox/projects/${pid}/scripts`),
  getScript: (sid) => request.get(`/apifox/scripts/${sid}`),
  createScript: (pid, data) => request.post(`/apifox/projects/${pid}/scripts`, data),
  updateScript: (sid, data) => request.put(`/apifox/scripts/${sid}`, data),
  deleteScript: (sid) => request.delete(`/apifox/scripts/${sid}`),

  listGlobalParams: (pid) => request.get(`/apifox/projects/${pid}/global-params`),
  createGlobalParam: (pid, data) => request.post(`/apifox/projects/${pid}/global-params`, data),
  updateGlobalParam: (gid, data) => request.put(`/apifox/global-params/${gid}`, data),
  deleteGlobalParam: (gid) => request.delete(`/apifox/global-params/${gid}`),

  listProjectCases: (pid) => request.get(`/apifox/projects/${pid}/cases`),
  listScenarios: (pid) => request.get(`/apifox/projects/${pid}/scenarios`),
  getScenario: (sid) => request.get(`/apifox/scenarios/${sid}`),
  createScenario: (pid, data) => request.post(`/apifox/projects/${pid}/scenarios`, data),
  updateScenario: (sid, data) => request.put(`/apifox/scenarios/${sid}`, data),
  deleteScenario: (sid) => request.delete(`/apifox/scenarios/${sid}`),
}

export const testExecutionApi = {
  listRuns: (projectId) =>
    request.get('/test-executions', { params: { project_id: projectId } }),
  getRun: (id) => request.get(`/test-executions/${id}`),
  createRun: (data) => request.post('/test-executions', data),
  updateRun: (id, data) => request.put(`/test-executions/${id}`, data),
  deleteRun: (id) => request.delete(`/test-executions/${id}`),
  submitCaseResult: (runId, caseRowId, data) =>
    request.put(`/test-executions/${runId}/cases/${caseRowId}`, data),
  listAvailableCases: (projectId, params = {}) =>
    request.get('/test-executions/available-cases/list', {
      params: { project_id: projectId, ...params },
    }),
}

export const apiAutomationApi = {
  listEnvironments: (projectId) =>
    request.get('/api-automation/environments', { params: { project_id: projectId } }),
  createEnvironment: (data) => request.post('/api-automation/environments', data),
  updateEnvironment: (id, data) => request.put(`/api-automation/environments/${id}`, data),
  deleteEnvironment: (id) => request.delete(`/api-automation/environments/${id}`),
  getGlobalVariables: (projectId) =>
    request.get(`/api-automation/projects/${projectId}/global-variables`),
  updateGlobalVariables: (projectId, data) =>
    request.put(`/api-automation/projects/${projectId}/global-variables`, data),
  listSuites: (projectId) =>
    request.get('/api-automation/suites', { params: { project_id: projectId } }),
  createSuite: (data) => request.post('/api-automation/suites', data),
  updateSuite: (id, data) => request.put(`/api-automation/suites/${id}`, data),
  deleteSuite: (id) => request.delete(`/api-automation/suites/${id}`),
  copySuite: (id) => request.post(`/api-automation/suites/${id}/copy`),
  listCases: (suiteId) => request.get('/api-automation/cases', { params: { suite_id: suiteId } }),
  createCase: (data) => request.post('/api-automation/cases', data),
  updateCase: (id, data) => request.put(`/api-automation/cases/${id}`, data),
  deleteCase: (id) => request.delete(`/api-automation/cases/${id}`),
  batchDeleteCases: (data) => request.post('/api-automation/cases/batch/delete', data),
  copyCase: (id, data = {}) => request.post(`/api-automation/cases/${id}/copy`, data),
  debugCase: (data) => request.post('/api-automation/cases/debug', data),
  generateCaseData: (data) => request.post('/api-automation/cases/generate-data', data),
  batchGenerateCaseData: (data) => request.post('/api-automation/cases/batch/generate-data', data),
  debugPreScript: (data) => request.post('/api-automation/scripts/pre/debug', data),
  debugPostScript: (data) => request.post('/api-automation/scripts/post/debug', data),
  runSuite: (suiteId) => request.post(`/api-automation/suites/${suiteId}/run`),
  runSuiteStream: (suiteId, onEvent, options = {}) => {
    const token = localStorage.getItem('token')
    return fetch(`/api/v1/api-automation/suites/${suiteId}/run/stream`, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      signal: options.signal,
    }).then(async (response) => {
      if (!response.ok) {
        let message = '请求失败'
        try {
          const body = await response.json()
          message = body.detail || message
        } catch {
          // ignore parse error
        }
        throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''
        for (const chunk of chunks) {
          const line = chunk.trim()
          if (!line.startsWith('data:')) continue
          const event = JSON.parse(line.slice(5).trim())
          onEvent(event)
        }
      }
    })
  },
  listRuns: (params = {}) => request.get('/api-automation/runs', { params }),
  getRun: (id) => request.get(`/api-automation/runs/${id}`),
  getCombinedRun: (runIds) =>
    request.get('/api-automation/runs/combined', { params: { run_ids: runIds.join(',') } }),
  deleteRun: (id) => request.delete(`/api-automation/runs/${id}`),
  batchDeleteRuns: (data) => request.post('/api-automation/runs/batch/delete', data),
  exportRun: (id, format = 'excel') =>
    request.get(`/api-automation/runs/${id}/export`, {
      params: { format },
      responseType: 'blob',
    }),
  batchExportRuns: (data) =>
    request.post('/api-automation/runs/batch/export', data, { responseType: 'blob' }),
  parseCapture: (data) => request.post('/api-automation/import/capture', { ...data, preview: true }),
  importCapture: (data) => request.post('/api-automation/import/capture', { ...data, preview: false }),
  parseSwagger: (data) => request.post('/api-automation/import/swagger', { ...data, preview: true }),
  importSwagger: (data) => request.post('/api-automation/import/swagger', { ...data, preview: false }),
  swaggerGenerateData: (data) => request.post('/api-automation/import/swagger/generate-data', data, { timeout: 300000 }),
  listSchedules: (projectId) => request.get('/api-automation/schedules', { params: { project_id: projectId } }),
  createSchedule: (data) => request.post('/api-automation/schedules', data),
  updateSchedule: (id, data) => request.put(`/api-automation/schedules/${id}`, data),
  deleteSchedule: (id) => request.delete(`/api-automation/schedules/${id}`),
  refreshSchedule: (id) => request.post(`/api-automation/schedules/${id}/refresh`),
  runScheduleNow: (id) => request.post(`/api-automation/schedules/${id}/run-now`),
}

export const logsApi = {
  sources: () => request.get('/logs/sources'),
  tail: (params = {}) => request.get('/logs/tail', { params }),
  integrations: (params = {}) => request.get('/logs/integrations', { params }),
  grafanaSession: () => request.post('/logs/grafana/session', {}, { withCredentials: true }),
  grafanaLaunch: (data, params = {}) => request.post('/logs/grafana/launch', data, { params }),
}

export default request

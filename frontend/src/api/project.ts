import { del, get, post, put, type Id } from './request'
import type { Schemas } from './types'

export type ProjectListParams = {
  page?: number
  page_size?: number
  keyword?: string
}

export type ProjectPageOut = {
  items: Schemas['ProjectOut'][]
  total: number
  page: number
  page_size: number
}

export type FunctionalOverviewOut = {
  case_total: number
  pending_review_count: number
  ai_generated_count: number
  ai_pending_review_count: number
  running_run_count: number
  last_completed_pass_rate: number | null
}

export type RequirementsOverviewOut = {
  req_total: number
  unreviewed_count: number
  linked_count: number
  unlinked_count: number
  ai_document_count: number
  ai_unreviewed_count: number
}

export type AiTasksOverviewOut = {
  total_task_count: number
  requirement_task_count: number
  case_task_count: number
  api_task_count: number
  active_api_task_count: number
}

export function isProjectPage(
  data: Schemas['ProjectOut'][] | ProjectPageOut,
): data is ProjectPageOut {
  return !Array.isArray(data)
}

export function unwrapProjectList(
  data: Schemas['ProjectOut'][] | ProjectPageOut,
): Schemas['ProjectOut'][] {
  return isProjectPage(data) ? data.items : data
}

export const projectApi = {
  list: (params: ProjectListParams = {}) =>
    get<Schemas['ProjectOut'][] | ProjectPageOut>('/projects', {
      params: Object.keys(params).length ? params : undefined,
    }),
  // opts.skipErrorToast：调用方自己提示（如工作区校验项目可访问性），不弹全局错误
  get: (id: Id, opts?: { skipErrorToast?: boolean }) =>
    get<Schemas['ProjectOut']>(`/projects/${id}`, opts),
  create: (data: Schemas['ProjectCreate']) => post<Schemas['ProjectOut']>('/projects', data),
  update: (id: Id, data: Schemas['ProjectUpdate']) =>
    put<Schemas['ProjectOut']>(`/projects/${id}`, data),
  delete: (id: Id) => del<void>(`/projects/${id}`),
  dashboard: () => get<Schemas['DashboardStats']>('/projects/stats/dashboard'),
  functionalOverview: (id: Id) => get<FunctionalOverviewOut>(`/projects/${id}/overview/functional`),
  requirementsOverview: (id: Id) =>
    get<RequirementsOverviewOut>(`/projects/${id}/overview/requirements`),
  aiTasksOverview: (id: Id) => get<AiTasksOverviewOut>(`/projects/${id}/overview/ai-tasks`),
  // 保存当前用户的置顶/排序偏好（items 按展示顺序：[{ project_id, pinned }]）
  savePreferences: (items: Schemas['ProjectPrefOrderIn']['items']) =>
    put<Schemas['ActionResultOut']>('/projects/preferences/order', { items }),
  // 项目成员（显式授权，管理需项目负责人/系统管理员）
  listMembers: (id: Id) => get<Schemas['ProjectMemberOut'][]>(`/projects/${id}/members`),
  memberCandidates: (id: Id, keyword?: string) =>
    get<Schemas['ProjectMemberCandidateOut'][]>(`/projects/${id}/member-candidates`, {
      params: keyword ? { keyword } : undefined,
    }),
  addMember: (id: Id, userId: number) =>
    post<Schemas['ProjectMemberOut']>(`/projects/${id}/members`, { user_id: userId }),
  removeMember: (id: Id, userId: number) =>
    del<{ message: string }>(`/projects/${id}/members/${userId}`),
}

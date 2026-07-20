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
  get: (id: Id) => get<Schemas['ProjectOut']>(`/projects/${id}`),
  create: (data: Schemas['ProjectCreate']) => post<Schemas['ProjectOut']>('/projects', data),
  update: (id: Id, data: Schemas['ProjectUpdate']) =>
    put<Schemas['ProjectOut']>(`/projects/${id}`, data),
  delete: (id: Id) => del<any>(`/projects/${id}`), // 无 response_model：any 占位（技术债）
  dashboard: () => get<Schemas['DashboardStats']>('/projects/stats/dashboard'),
  // 保存当前用户的置顶/排序偏好（items 按展示顺序：[{ project_id, pinned }]）
  savePreferences: (items: Schemas['ProjectPrefOrderIn']['items']) =>
    put<any>('/projects/preferences/order', { items }),
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

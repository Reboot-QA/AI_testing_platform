import { del, get, post, put, type Id } from './request'
import type { Schemas } from './types'

export const projectApi = {
  list: () => get<Schemas['ProjectOut'][]>('/projects'),
  get: (id: Id) => get<Schemas['ProjectOut']>(`/projects/${id}`),
  create: (data: Schemas['ProjectCreate']) => post<Schemas['ProjectOut']>('/projects', data),
  update: (id: Id, data: Schemas['ProjectUpdate']) =>
    put<Schemas['ProjectOut']>(`/projects/${id}`, data),
  delete: (id: Id) => del<any>(`/projects/${id}`), // 无 response_model：any 占位（技术债）
  dashboard: () => get<Schemas['DashboardStats']>('/projects/stats/dashboard'),
  // 保存当前用户的置顶/排序偏好（items 按展示顺序：[{ project_id, pinned }]）
  savePreferences: (items: Schemas['ProjectPrefOrderIn']['items']) =>
    put<any>('/projects/preferences/order', { items }),
}

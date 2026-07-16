import { del, get, post, put, type Id } from './request'
import type { Schemas } from './types'

export const departmentApi = {
  list: () => get<Schemas['DepartmentOut'][]>('/departments'),
  create: (data: Schemas['DepartmentCreate']) =>
    post<Schemas['DepartmentOut']>('/departments', data),
  update: (id: Id, data: Schemas['DepartmentUpdate']) =>
    put<Schemas['DepartmentOut']>(`/departments/${id}`, data),
  delete: (id: Id) => del<any>(`/departments/${id}`), // 无 response_model（技术债）
  getPermissions: (id: Id) =>
    get<Schemas['DepartmentPermissionsOut']>(`/departments/${id}/permissions`),
  updatePermissions: (
    id: Id,
    menu_permissions: Schemas['DepartmentPermissionsUpdate']['menu_permissions'],
  ) =>
    put<Schemas['DepartmentPermissionsOut']>(`/departments/${id}/permissions`, {
      menu_permissions,
    }),
}

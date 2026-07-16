import { del, get, post, put, type Id } from './request'
import type { Schemas } from './types'

export const userApi = {
  list: () => get<Schemas['UserOut'][]>('/users'),
  create: (data: Schemas['UserCreateByAdmin']) => post<Schemas['UserOut']>('/users', data),
  update: (id: Id, data: Schemas['UserUpdate']) => put<Schemas['UserOut']>(`/users/${id}`, data),
  resetPassword: (id: Id, password: Schemas['UserPasswordReset']['password']) =>
    put<any>(`/users/${id}/password`, { password }), // 无 response_model（技术债）
  delete: (id: Id) => del<any>(`/users/${id}`), // 无 response_model（技术债）
  listMenus: () => get<Schemas['MenuDefinitionOut'][]>('/users/menus'),
  getPermissions: (id: Id) => get<Schemas['UserPermissionsOut']>(`/users/${id}/permissions`),
  updatePermissions: (
    id: Id,
    menu_permissions: Schemas['UserPermissionsUpdate']['menu_permissions'],
  ) => put<Schemas['UserPermissionsOut']>(`/users/${id}/permissions`, { menu_permissions }),
}

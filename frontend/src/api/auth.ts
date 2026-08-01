import { get, post, put } from './request'
import type { Schemas } from './types'

export const authApi = {
  login: (username: string, password: string) => {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    return post<Schemas['Token']>('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  register: (data: Schemas['UserCreate']) => post<Schemas['UserOut']>('/auth/register', data),
  me: () => get<Schemas['UserOut']>('/auth/me'),
  updateProfile: (data: Schemas['UserProfileUpdate']) => put<Schemas['UserOut']>('/auth/me', data),
  logout: (token?: string) =>
    post<{ message: string }>('/auth/logout', undefined, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }),
  changePassword: (data: Schemas['UserPasswordChange']) =>
    put<Schemas['ActionResultOut']>('/auth/password', data),
}

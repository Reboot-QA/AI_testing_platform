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
  // 无 response_model（返回 {message}）：any 弱类型占位（技术债：后端补 response_model）
  changePassword: (data: Schemas['UserPasswordChange']) => put<any>('/auth/password', data),
}

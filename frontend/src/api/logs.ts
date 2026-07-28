import { get } from './request'

// logs 模块全部无 response_model（返回自由结构）：any 弱类型占位（技术债：后端补 response_model）
export const logsApi = {
  sources: () => get<any>('/logs/sources'),
  tail: (params: Record<string, unknown> = {}) => get<any>('/logs/tail', { params }),
}

export const errorLogsApi = {
  summary: () => get<any>('/logs/errors/summary'),
  tail: (params: Record<string, unknown> = {}) => get<any>('/logs/errors/tail', { params }),
}

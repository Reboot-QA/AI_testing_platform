// API 层公共封装：axios 实例 + 拦截器 + 泛型请求方法 + SSE 公共封装。
// 各域模块（auth/project/...）只声明端点，统一从这里取 get/post/put/patch/del/streamSSE。
import axios, { type AxiosRequestConfig } from 'axios'
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
    // apifox 保存冲突(409 乐观锁)：交由调用方自定义处理，不弹通用错误。
    // 收窄到 /apifox/，避免吞掉其他模块用 409 表达的别的语义。
    if (error.response?.status === 409 && (error.config?.url || '').includes('/apifox/')) {
      return Promise.reject(error)
    }
    const msg = error.response?.data?.detail || error.message || '请求失败'
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    ElMessage.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    return Promise.reject(error)
  },
)

// 路径 id：URL 拼接既可能收到 number 也可能收到路由字符串。
export type Id = number | string

// 响应拦截器已解包 response.data，故第二泛型 R=T，方法直接 resolve 出后端返回体。
export function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return request.get<T, T>(url, config)
}
export function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request.post<T, T>(url, data, config)
}
export function put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request.put<T, T>(url, data, config)
}
export function patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  return request.patch<T, T>(url, data, config)
}
export function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  return request.delete<T, T>(url, config)
}

// SSE 事件无 response_model，按弱类型占位（技术债：后端补类型）。
export type SSEEvent = any

export interface StreamSSEOptions {
  method?: string
  body?: BodyInit | null
  headers?: Record<string, string>
  signal?: AbortSignal
  onEvent: (event: SSEEvent) => void
}

// 收敛原先 4 份重复的 SSE 解析（extract/aiGenerate/chat/apifoxRun）：
// 带 token、`data:` 分块解析、按 \n\n 切分、非 2xx 抛后端 detail。
export async function streamSSE(url: string, opts: StreamSSEOptions): Promise<void> {
  const token = localStorage.getItem('token')
  const response = await fetch(url, {
    method: opts.method ?? 'POST',
    headers: {
      ...(opts.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: opts.body ?? undefined,
    signal: opts.signal,
  })

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

  if (!response.body) return
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
      opts.onEvent(JSON.parse(line.slice(5).trim()))
    }
  }
}

export default request

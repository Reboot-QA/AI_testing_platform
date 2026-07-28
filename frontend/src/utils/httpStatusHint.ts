/** 调试/运行响应：状态码与 Body 的中文摘要（如 Token 失效 → 无权限） */

function responseDetail(body: unknown): string {
  if (body == null) return ''
  if (typeof body === 'string') return body
  if (typeof body === 'object' && body !== null && 'detail' in body) {
    const d = (body as { detail: unknown }).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d)) return d.map(String).join(' ')
  }
  return ''
}

export function httpStatusHint(status: number | null | undefined, body?: unknown): string {
  if (status === 401) return '无权限'
  if (status === 403) return '禁止访问'
  const detail = responseDetail(body)
  if (!detail) return ''
  if (/无效.*认证|认证.*无效|凭据|未授权|无权限|Unauthorized|Forbidden/i.test(detail)) {
    return status === 403 ? '禁止访问' : '无权限'
  }
  return ''
}

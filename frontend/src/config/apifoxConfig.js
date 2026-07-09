// Apifox 视觉配置表（移植自参考项目 configs/static.ts）。颜色引用 tokens.css 的 CSS 变量。

// HTTP 方法 → 展示文案 + 色。文案沿用 Apifox 缩写以控制宽度。
export const HTTP_METHOD_CONFIG = {
  GET: { text: 'GET', color: 'var(--color-green-6)' },
  POST: { text: 'POST', color: 'var(--color-orange-6)' },
  PUT: { text: 'PUT', color: 'var(--color-blue-6)' },
  DELETE: { text: 'DEL', color: 'var(--color-volcano-6)' },
  PATCH: { text: 'PATCH', color: 'var(--color-pink-6)' },
  HEAD: { text: 'HEAD', color: 'var(--color-blue-6)' },
  OPTIONS: { text: 'OPT', color: 'var(--color-blue-6)' },
  TRACE: { text: 'TRACE', color: 'var(--color-geekblue-6)' },
}

export function methodConfig(method) {
  return HTTP_METHOD_CONFIG[String(method || '').toUpperCase()] || HTTP_METHOD_CONFIG.GET
}

// 接口状态 → 文案 + 色（10 种）。
export const API_STATUS_CONFIG = {
  designing: { text: '设计中', color: 'var(--color-lime-6)' },
  pending: { text: '待确定', color: 'var(--color-yellow-6)' },
  developing: { text: '开发中', color: 'var(--color-blue-6)' },
  obsolete: { text: '已废弃', color: 'var(--color-grey-6)' },
  integrating: { text: '联调中', color: 'var(--color-pink-6)' },
  testing: { text: '测试中', color: 'var(--color-orange-6)' },
  tested: { text: '已测完', color: 'var(--color-purple-6)' },
  released: { text: '已发布', color: 'var(--color-green-6)' },
  deprecated: { text: '将废弃', color: 'var(--color-grey-6)' },
  exception: { text: '有异常', color: 'var(--color-red-6)' },
}

// HTTP 状态码 → 文案。
export const HTTP_CODE_CONFIG = {
  200: '成功',
  201: '成功',
  202: '成功',
  204: '删除成功',
  400: '请求有误',
  401: '没有权限',
  403: '禁止访问',
  404: '记录不存在',
  410: '记录不存在',
  422: '参数错误',
  500: '服务器错误',
  502: '网关错误',
  503: '服务器故障',
  504: '网关超时',
}

export function httpCodeText(code) {
  return HTTP_CODE_CONFIG[Number(code)] || ''
}

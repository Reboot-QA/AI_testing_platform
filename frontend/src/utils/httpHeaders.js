// header 名/值自动补全用的常用清单 + 键值行↔文本的批量互转
import { emptyKvRow } from '@/utils/apiCaseConfig'

export const COMMON_HEADERS = [
  'Accept', 'Accept-Encoding', 'Accept-Language', 'Authorization', 'Cache-Control',
  'Connection', 'Content-Type', 'Content-Length', 'Cookie', 'Host', 'Origin',
  'Referer', 'User-Agent', 'X-Requested-With', 'X-Request-Id', 'If-None-Match',
  'If-Modified-Since', 'Range', 'Pragma',
]

const VALUE_SUGGESTIONS = {
  'content-type': [
    'application/json', 'application/xml', 'application/x-www-form-urlencoded',
    'multipart/form-data', 'text/plain', 'text/html', 'application/octet-stream',
  ],
  accept: ['application/json', 'application/xml', '*/*', 'text/plain', 'text/html'],
  connection: ['keep-alive', 'close'],
  'cache-control': ['no-cache', 'no-store', 'max-age=0'],
  'accept-encoding': ['gzip, deflate, br', 'gzip', 'identity'],
  authorization: ['Bearer ', 'Basic '],
  pragma: ['no-cache'],
}

// 「常用 Header → 默认值」单一数据源：既供勾选区展示，也供 autocomplete 选中时自动填值
export const COMMON_HEADER_PRESETS = [
  { name: 'Content-Type', value: 'application/json' },
  { name: 'Accept', value: '*/*' },
  { name: 'Authorization', value: 'Bearer ' },
  { name: 'Accept-Encoding', value: 'gzip, deflate, br' },
  { name: 'Accept-Language', value: 'zh-CN,zh;q=0.9' },
  { name: 'Cache-Control', value: 'no-cache' },
  { name: 'Connection', value: 'keep-alive' },
  { name: 'User-Agent', value: 'Apifox/1.0.0 (https://apifox.com)' },
  { name: 'X-Requested-With', value: 'XMLHttpRequest' },
]

const _defaultByKey = Object.fromEntries(COMMON_HEADER_PRESETS.map((h) => [h.name.toLowerCase(), h.value]))

export function headerDefaultValue(key) {
  return _defaultByKey[(key || '').trim().toLowerCase()] || ''
}

// el-autocomplete fetch-suggestions 结果格式：[{ value }]
export function suggestHeaderKeys(query) {
  const q = (query || '').toLowerCase()
  return COMMON_HEADERS.filter((h) => h.toLowerCase().includes(q)).map((value) => ({ value }))
}

export function suggestHeaderValues(key, query) {
  const list = VALUE_SUGGESTIONS[(key || '').trim().toLowerCase()] || []
  const q = (query || '').toLowerCase()
  return list.filter((v) => v.toLowerCase().includes(q)).map((value) => ({ value }))
}

// 行 → 文本（批量编辑用）：禁用行以 // 前缀标注，空行跳过
export function rowsToText(rows) {
  return (rows || [])
    .filter((r) => (r.key || '').trim() || (r.value || '').trim())
    .map((r) => `${r.enabled === false ? '// ' : ''}${r.key || ''}: ${r.value || ''}`)
    .join('\n')
}

// 文本 → 行：每行 `Key: Value`，// 或 # 开头表示禁用；无冒号则整行当键
export function textToRows(text) {
  return (text || '')
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      let enabled = true
      let rest = line
      if (rest.startsWith('//') || rest.startsWith('#')) {
        enabled = false
        rest = rest.replace(/^(\/\/|#)\s*/, '')
      }
      const idx = rest.indexOf(':')
      const key = idx >= 0 ? rest.slice(0, idx).trim() : rest.trim()
      const value = idx >= 0 ? rest.slice(idx + 1).trim() : ''
      return { ...emptyKvRow(), key, value, enabled }
    })
}

// header 名/值自动补全用的常用清单 + 键值行↔文本的批量互转
import { emptyKvRow } from '@/utils/apiCaseConfig'
import type { KvRow } from '@/types/apifox'

export const COMMON_HEADERS = [
  'Accept',
  'Accept-Encoding',
  'Accept-Language',
  'Authorization',
  'Cache-Control',
  'Connection',
  'Content-Type',
  'Content-Length',
  'Cookie',
  'Host',
  'Origin',
  'Referer',
  'User-Agent',
  'X-Requested-With',
  'X-Request-Id',
  'If-None-Match',
  'If-Modified-Since',
  'Range',
  'Pragma',
] as const

const VALUE_SUGGESTIONS: Record<string, string[]> = {
  'content-type': [
    'application/json',
    'application/xml',
    'application/x-www-form-urlencoded',
    'multipart/form-data',
    'text/plain',
    'text/html',
    'application/octet-stream',
  ],
  accept: ['application/json', 'application/xml', '*/*', 'text/plain', 'text/html'],
  connection: ['keep-alive', 'close'],
  'cache-control': ['no-cache', 'no-store', 'max-age=0'],
  'accept-encoding': ['gzip, deflate, br', 'gzip', 'identity'],
  authorization: ['Bearer ', 'Basic '],
  pragma: ['no-cache'],
}

export interface HeaderPreset {
  name: string
  value: string
}

// 「常用 Header → 默认值」单一数据源：既供勾选区展示，也供 autocomplete 选中时自动填值
export const COMMON_HEADER_PRESETS: HeaderPreset[] = [
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

const _defaultByKey = Object.fromEntries(
  COMMON_HEADER_PRESETS.map((h) => [h.name.toLowerCase(), h.value]),
)

export function headerDefaultValue(key: string | null | undefined): string {
  return _defaultByKey[(key || '').trim().toLowerCase()] || ''
}

export function suggestHeaderKeys(query: string | null | undefined): Array<{ value: string }> {
  const q = (query || '').toLowerCase()
  return COMMON_HEADERS.filter((h) => h.toLowerCase().includes(q)).map((value) => ({ value }))
}

export function suggestHeaderValues(
  key: string | null | undefined,
  query: string | null | undefined,
): Array<{ value: string }> {
  const list = VALUE_SUGGESTIONS[(key || '').trim().toLowerCase()] || []
  const q = (query || '').toLowerCase()
  return list.filter((v) => v.toLowerCase().includes(q)).map((value) => ({ value }))
}

export function rowsToText(rows: KvRow[] | null | undefined): string {
  return (rows || [])
    .filter((r) => (r.key || '').trim() || (r.value || '').trim())
    .map((r) => `${r.enabled === false ? '// ' : ''}${r.key || ''}: ${r.value || ''}`)
    .join('\n')
}

export function textToRows(text: string | null | undefined): KvRow[] {
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

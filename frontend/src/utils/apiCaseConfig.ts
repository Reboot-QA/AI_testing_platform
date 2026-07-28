// 用例配置模块：apifox 用例表单里 KV 行、变量名、提取来源/变量作用域选项的工具。
// 类型定义集中在 types/apifox.ts。
import type { EditorVariable, ExtractSourceOption, KvRow } from '@/types/apifox'

export function emptyKvRow(): KvRow {
  return { key: '', value: '', enabled: true, desc: '', type: 'string' }
}

export const EXTRACT_SOURCE_OPTIONS: ExtractSourceOption[] = [
  {
    value: 'response_json',
    label: 'Response JSON',
    pathLabel: 'JSONPath 表达式',
    placeholder: '$.data.token',
  },
  {
    value: 'response_xml',
    label: 'Response XML',
    pathLabel: 'XML 路径',
    placeholder: 'token 或 //token',
  },
  {
    value: 'response_text',
    label: 'Response Text',
    pathLabel: '正则/留空',
    placeholder: '留空取全文，或 regex:pattern',
  },
  {
    value: 'response_header',
    label: 'Response Header',
    pathLabel: 'Header 名称',
    placeholder: 'X-Trace-Id',
  },
  {
    value: 'response_cookie',
    label: 'Response Cookie',
    pathLabel: 'Cookie 名称',
    placeholder: 'session_id',
  },
  {
    value: 'response_time',
    label: '响应时间',
    pathLabel: '（无需填写）',
    placeholder: '自动提取毫秒数',
  },
  {
    value: 'request_header',
    label: 'Request Header',
    pathLabel: 'Header 名称',
    placeholder: 'Authorization',
  },
  {
    value: 'request_body',
    label: 'Request Body',
    pathLabel: 'JSONPath 表达式',
    placeholder: '$.username',
  },
]

export const VARIABLE_SCOPE_OPTIONS = [
  { value: 'temporary', label: '临时变量', tip: '单次运行结束后消失，仅在当前流程内有效' },
  {
    value: 'environment',
    label: '环境变量',
    tip: '随环境保存，切换环境后互不影响（推荐 Token 等）',
  },
  { value: 'global', label: '全局变量', tip: '跨所有环境永久有效，除非手动删除' },
]

export function normalizeExtractScope(scope: string | null | undefined): string {
  const normalized = String(scope || 'temporary').toLowerCase()
  return VARIABLE_SCOPE_OPTIONS.some((item) => item.value === normalized) ? normalized : 'temporary'
}

export const VARIABLE_SCOPE_LABELS: Record<string, string> = {
  case: '用例变量',
  temporary: '临时变量',
  environment: '环境变量',
  global: '全局变量',
  extract: '提取变量',
}

/** 从接口/用例后置处理器（ProcessorRow）收集提取变量名，供 {{ 联想 */
export function collectProcessorExtractVariables(
  processors: Array<{
    kind?: string
    enabled?: boolean
    var_name?: string | null
    scope?: string | null
  }> = [],
  extractedVariables: Record<string, string> = {},
): EditorVariable[] {
  const vars: EditorVariable[] = []
  const seen = new Set<string>()
  processors
    .filter((p) => p.kind === 'extract' && p.enabled !== false)
    .forEach((p) => {
      const name = (p.var_name || '').trim()
      if (!name || seen.has(name)) return
      seen.add(name)
      vars.push({
        name,
        value: extractedVariables[name] ?? '（运行后提取）',
        scope: normalizeExtractScope(p.scope),
        scopeLabel: `后置提取 · ${VARIABLE_SCOPE_LABELS[normalizeExtractScope(p.scope)] || '临时变量'}`,
      })
    })
  return vars
}

export function variableNamesFromRows(variableRows: KvRow[] | null | undefined): string[] {
  return (variableRows || [])
    .filter((row) => row.enabled !== false && (row.key || '').trim())
    .map((row) => row.key.trim())
}

// 始终保证恰好一个末尾空行（与 KvRowsEditor.syncTail 的不变量一致）：
// 否则编辑器挂载时补空行会改动 form，导致"打开即脏"的未保存误判。
export function ensureKvRows(rows: KvRow[] | null | undefined): KvRow[] {
  const list = Array.isArray(rows) ? [...rows] : []
  const last = list[list.length - 1]
  const lastEmpty = last && !(last.key || '').trim() && !(last.value || '').trim()
  if (!lastEmpty) list.push(emptyKvRow())
  return list
}

/**
 * 断言结果 → 展示项（调试面板 DebugResponsePanel 与运行报告 RunStepDetailPanel 共用）。
 *
 * 两类来源合并：
 * 1. 声明式断言 assertion_results：补出「类型 + 期望/实际」，失败时便于定位（后端本就返回 expected/actual）。
 * 2. 脚本断言 pm.test：结果只以字符串塞在 script_logs（`✓ 名称` / `✗ 名称 | 错误`），这里解析出来并入断言 tab。
 */

export interface AssertionItem {
  passed: boolean
  label: string
  message: string
}

const TYPE_LABELS: Record<string, string> = {
  status_code: '状态码',
  json_path: 'JSON路径',
  header: '响应头',
  contains: '包含',
  response_time: '响应时长',
}

function toText(value: unknown): string {
  return value === null || value === undefined ? '' : String(value)
}

/** 声明式断言：`[类型] message`，失败再补「期望: X ｜ 实际: Y」 */
function declarativeItems(results: readonly Record<string, unknown>[]): AssertionItem[] {
  return results.map((a) => {
    const passed = !!a.passed
    const type = toText(a.type)
    const typeLabel = TYPE_LABELS[type] || type
    const msg = typeof a.message === 'string' ? a.message : ''
    const parts: string[] = []
    if (typeLabel) parts.push(`[${typeLabel}]`)
    if (msg) parts.push(msg)
    if (!passed && (a.expected != null || a.actual != null)) {
      parts.push(`期望: ${toText(a.expected)} ｜ 实际: ${toText(a.actual)}`)
    }
    return { passed, label: passed ? '通过' : '失败', message: parts.join(' ') }
  })
}

// pm.test 结果行：库引用脚本会带 `[脚本名] ` 前缀，故 ✓/✗ 允许出现在行首或 `] ` 之后
const SCRIPT_ASSERTION_RE = /(?:^|\]\s)([✓✗])\s+(.+)$/

/** 脚本断言（pm.test 的 ✓/✗ 行）→ 断言项；非断言的普通日志忽略 */
function scriptAssertionItems(scriptLogs: readonly string[]): AssertionItem[] {
  const items: AssertionItem[] = []
  for (const line of scriptLogs) {
    const m = SCRIPT_ASSERTION_RE.exec(line)
    if (!m) continue
    const passed = m[1] === '✓'
    items.push({ passed, label: passed ? '通过' : '失败', message: `[脚本] ${m[2]}` })
  }
  return items
}

export function toAssertionItems(
  results: readonly Record<string, unknown>[] | null | undefined,
  scriptLogs: readonly string[] | null | undefined,
): AssertionItem[] {
  return [...declarativeItems(results ?? []), ...scriptAssertionItems(scriptLogs ?? [])]
}

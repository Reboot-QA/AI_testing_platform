// 把用例断言渲染成「状态码 = 200」这类可读短语，帮用户在 AI 生成预览时判断用例意图。
type Assertion = {
  type?: string
  path?: string | null
  operator?: string
  expected?: string | null
  enabled?: boolean
}

export function summarizeAssertions(caseItem: { assertions?: Assertion[] }): string {
  const rows = (caseItem.assertions || []).filter((a) => a.enabled !== false)
  if (!rows.length) return '无断言'
  return rows
    .slice(0, 3)
    .map((a) => {
      const target = a.type === 'status_code' ? '状态码' : a.path || a.type
      return `${target} ${a.operator} ${a.expected ?? ''}`.trim()
    })
    .join(' · ')
}

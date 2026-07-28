export const CASE_TYPE_LABELS: Record<string, string> = {
  functional: '功能',
  api: '接口',
  performance: '性能',
  security: '安全',
}

export function formatCaseTypeLabel(value?: string | null): string {
  if (!value) return '-'
  return CASE_TYPE_LABELS[value] || value
}

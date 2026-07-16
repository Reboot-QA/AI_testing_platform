// 单接口用例分类（对齐 Apifox）· 值↔中文标签，前后端一致
export interface CaseCategory {
  value: string
  label: string
}

export const CASE_CATEGORIES: CaseCategory[] = [
  { value: 'positive', label: '正向' },
  { value: 'negative', label: '逆向' },
  { value: 'boundary', label: '边界值' },
  { value: 'security', label: '安全性' },
  { value: 'other', label: '其他' },
]

const _map: Record<string, string> = Object.fromEntries(
  CASE_CATEGORIES.map((c) => [c.value, c.label]),
)

export function categoryLabel(value: string): string {
  return _map[value] || '其他'
}

// 过滤条用：在分类前加「全部」
export const CATEGORY_FILTERS: CaseCategory[] = [
  { value: 'all', label: '全部' },
  ...CASE_CATEGORIES,
]

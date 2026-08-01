/** \u62a5\u544a\u5217\u8868\u7b5b\u9009\u6587\u6848\uff08\u907f\u514d\u6e90\u6587\u4ef6\u7f16\u7801\u635f\u574f\uff09 */

export type RunListFilter = 'all' | 'passed' | 'failed'

export const RUN_LIST_FILTER_LABELS: Record<RunListFilter, string> = {
  all: '\u5168\u90e8',
  passed: '\u901a\u8fc7',
  failed: '\u5931\u8d25',
}

export const RUN_LIST_SEARCH_CASE = '\u641c\u7d22\u7528\u4f8b\u540d\u79f0'
export const RUN_LIST_SEARCH_SUITE = '\u641c\u7d22\u5957\u4ef6\u9879\u540d\u79f0'
export const RUN_LIST_UNNAMED = '\u672a\u547d\u540d'

export function runListEmptyHint(filter: RunListFilter, hasKeyword: boolean): string {
  if (hasKeyword) return '\u65e0\u5339\u914d\u7528\u4f8b'
  if (filter === 'failed') return '\u6ca1\u6709\u5931\u8d25\u7528\u4f8b'
  if (filter === 'passed') return '\u6ca1\u6709\u901a\u8fc7\u7528\u4f8b'
  return '\u6682\u65e0\u7528\u4f8b'
}

export function buildRunListFilterTabs(counts: { all: number; passed: number; failed: number }) {
  return (['all', 'passed', 'failed'] as const).map((value) => ({
    value,
    label: RUN_LIST_FILTER_LABELS[value],
    count: counts[value],
  }))
}

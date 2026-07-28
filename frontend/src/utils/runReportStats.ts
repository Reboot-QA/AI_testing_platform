import type { Schemas } from '@/api/types'

type RunStep = Schemas['RunStepOut']

export interface RunStepStats {
  requestTimeMs: number
  avgRequestMs: number
  httpCount: number
  httpFailed: number
  assertionTotal: number
  assertionFailed: number
}

export function computeRunStepStats(steps: RunStep[]): RunStepStats {
  const httpSteps = steps.filter((s) => s.method || s.url)
  const durations = httpSteps.map((s) => s.duration_ms ?? 0).filter((d) => d > 0)
  const requestTimeMs = durations.reduce((sum, d) => sum + d, 0)

  let assertionTotal = 0
  let assertionFailed = 0
  for (const step of steps) {
    for (const row of step.assertion_results || []) {
      assertionTotal += 1
      if (!row.passed) assertionFailed += 1
    }
  }

  return {
    requestTimeMs,
    avgRequestMs: durations.length ? requestTimeMs / durations.length : 0,
    httpCount: httpSteps.length,
    httpFailed: httpSteps.filter((s) => s.status !== 'passed').length,
    assertionTotal,
    assertionFailed,
  }
}

export function displayRequestPath(url: string): string {
  if (!url) return ''
  try {
    if (url.startsWith('http://') || url.startsWith('https://')) {
      const u = new URL(url)
      return u.pathname + u.search
    }
  } catch {
    // 非标准 URL 原样展示
  }
  return url
}

export function formatReportDuration(ms: number | null | undefined): string {
  if (ms == null) return '-'
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`
  return `${ms.toFixed(2)}ms`
}

export function pct(part: number, total: number): string {
  if (total <= 0) return '0%'
  return `${((part / total) * 100).toFixed(2).replace(/\.?0+$/, '')}%`
}

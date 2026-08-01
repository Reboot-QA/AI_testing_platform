import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/types'
import {
  computeRunStepStats,
  displayRequestPath,
  formatReportDuration,
  pct,
} from '@/utils/runReportStats'

type RunStep = Schemas['RunStepOut']

function step(partial: Partial<RunStep> & Pick<RunStep, 'id' | 'status'>): RunStep {
  return {
    step_type: 'http',
    depth: 0,
    iteration: 0,
    loop_round: 0,
    case_name: '',
    method: '',
    url: '',
    duration_ms: 0,
    request_headers: {},
    request_body: '',
    response_headers: {},
    response_body: '',
    assertion_results: [],
    extract_results: [],
    script_logs: [],
    error_message: '',
    ...partial,
  }
}

describe('computeRunStepStats', () => {
  it('空步骤全零', () => {
    expect(computeRunStepStats([])).toEqual({
      requestTimeMs: 0,
      avgRequestMs: 0,
      httpCount: 0,
      httpFailed: 0,
      assertionTotal: 0,
      assertionFailed: 0,
    })
  })

  it('统计 HTTP 耗时、失败与断言', () => {
    const steps = [
      step({
        id: 1,
        status: 'passed',
        method: 'GET',
        url: '/a',
        duration_ms: 100,
        assertion_results: [{ passed: true }, { passed: false }],
      }),
      step({
        id: 2,
        status: 'failed',
        method: 'POST',
        url: '/b',
        duration_ms: 50,
        assertion_results: [{ passed: false }],
      }),
      step({ id: 3, status: 'passed', method: '', url: '', duration_ms: 999 }),
    ]
    const stats = computeRunStepStats(steps)
    expect(stats.httpCount).toBe(2)
    expect(stats.httpFailed).toBe(1)
    expect(stats.requestTimeMs).toBe(150)
    expect(stats.avgRequestMs).toBe(75)
    expect(stats.assertionTotal).toBe(3)
    expect(stats.assertionFailed).toBe(2)
  })

  it('duration_ms <= 0 不计入请求耗时', () => {
    const stats = computeRunStepStats([
      step({ id: 1, status: 'passed', method: 'GET', url: '/a', duration_ms: 0 }),
      step({ id: 2, status: 'passed', method: 'GET', url: '/b', duration_ms: -1 }),
    ])
    expect(stats.requestTimeMs).toBe(0)
    expect(stats.avgRequestMs).toBe(0)
    expect(stats.httpCount).toBe(2)
  })
})

describe('displayRequestPath', () => {
  it('空串返回空', () => {
    expect(displayRequestPath('')).toBe('')
  })

  it('绝对 URL 只保留 path + search', () => {
    expect(displayRequestPath('https://api.example.com/v1/users?id=1')).toBe('/v1/users?id=1')
  })

  it('相对路径与非法 URL 原样返回', () => {
    expect(displayRequestPath('/relative')).toBe('/relative')
    expect(displayRequestPath('http://[bad')).toBe('http://[bad')
  })
})

describe('formatReportDuration', () => {
  it('null/undefined 为 -', () => {
    expect(formatReportDuration(null)).toBe('-')
    expect(formatReportDuration(undefined)).toBe('-')
  })

  it('>=1000ms 用秒，否则用毫秒', () => {
    expect(formatReportDuration(1234)).toBe('1.23s')
    expect(formatReportDuration(12.345)).toBe('12.35ms')
  })
})

describe('pct', () => {
  it('total<=0 返回 0%', () => {
    expect(pct(1, 0)).toBe('0%')
    expect(pct(0, -1)).toBe('0%')
  })

  it('去掉多余尾零', () => {
    expect(pct(1, 2)).toBe('50%')
    expect(pct(1, 3)).toBe('33.33%')
  })
})

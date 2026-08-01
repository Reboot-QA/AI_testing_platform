import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  formatBeijingTime,
  formatBeijingWallClock,
  formatRelativeTime,
  parseShanghaiNaiveDateTime,
} from '@/utils/datetime'

describe('parseShanghaiNaiveDateTime', () => {
  it('空值与非法返回 null', () => {
    expect(parseShanghaiNaiveDateTime(null)).toBeNull()
    expect(parseShanghaiNaiveDateTime('')).toBeNull()
    expect(parseShanghaiNaiveDateTime('not-a-date')).toBeNull()
    expect(parseShanghaiNaiveDateTime(Number.NaN)).toBeNull()
  })

  it('Date / number 原样透传', () => {
    const d = new Date('2024-01-01T00:00:00Z')
    expect(parseShanghaiNaiveDateTime(d)).toBe(d)
    expect(parseShanghaiNaiveDateTime(d.getTime())!.getTime()).toBe(d.getTime())
  })

  it('无时区字符串按 +08:00 解析', () => {
    const d = parseShanghaiNaiveDateTime('2024-06-01 12:00:00')
    expect(d).not.toBeNull()
    // 北京 12:00 = UTC 04:00
    expect(d!.toISOString()).toBe('2024-06-01T04:00:00.000Z')
  })
})

describe('formatBeijingTime / formatBeijingWallClock', () => {
  it('无效输入返回 fallback', () => {
    expect(formatBeijingTime(null)).toBe('-')
    expect(formatBeijingTime('bad', 'N/A')).toBe('N/A')
    expect(formatBeijingWallClock(undefined, '--')).toBe('--')
  })

  it('UTC 时间格式化为北京时间字符串', () => {
    const text = formatBeijingTime('2024-01-01T00:00:00Z')
    expect(text).toContain('2024')
    expect(text).toMatch(/08:00:00/)
  })

  it('wall clock 对 naive 字符串按上海时区展示', () => {
    const text = formatBeijingWallClock('2024-06-01 12:30:00')
    expect(text).toMatch(/12:30:00/)
  })
})

describe('formatRelativeTime', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('无效输入返回 fallback', () => {
    expect(formatRelativeTime(null)).toBe('-')
  })

  it('按差值返回相对文案，超过 7 天回退北京时间', () => {
    const now = new Date('2024-06-15T12:00:00Z')
    vi.useFakeTimers()
    vi.setSystemTime(now)

    expect(formatRelativeTime(new Date(now.getTime() - 30_000))).toBe('刚刚')
    expect(formatRelativeTime(new Date(now.getTime() - 5 * 60_000))).toBe('5 分钟前')
    expect(formatRelativeTime(new Date(now.getTime() - 3 * 3600_000))).toBe('3 小时前')
    expect(formatRelativeTime(new Date(now.getTime() - 2 * 86400_000))).toBe('2 天前')
    const old = formatRelativeTime(new Date(now.getTime() - 10 * 86400_000))
    expect(old).not.toMatch(/前$/)
    expect(old).toContain('2024')
  })
})

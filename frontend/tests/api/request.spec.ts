import { describe, expect, it } from 'vitest'
import { isUnauthorizedError } from '@/api/request'

describe('isUnauthorizedError', () => {
  it('非对象 / 无 response 返回 false', () => {
    expect(isUnauthorizedError(null)).toBe(false)
    expect(isUnauthorizedError(undefined)).toBe(false)
    expect(isUnauthorizedError('401')).toBe(false)
    expect(isUnauthorizedError({})).toBe(false)
    expect(isUnauthorizedError({ response: {} })).toBe(false)
  })

  it('仅 HTTP 401 为 true，其它状态码为 false', () => {
    expect(isUnauthorizedError({ response: { status: 401 } })).toBe(true)
    expect(isUnauthorizedError({ response: { status: 403 } })).toBe(false)
    expect(isUnauthorizedError({ response: { status: 500 } })).toBe(false)
  })
})

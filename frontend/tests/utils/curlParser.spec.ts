import { describe, expect, it } from 'vitest'
import { parseCurl } from '@/utils/curlParser'

describe('parseCurl', () => {
  it('非 curl 或空输入返回 null', () => {
    expect(parseCurl(null)).toBeNull()
    expect(parseCurl(undefined)).toBeNull()
    expect(parseCurl('')).toBeNull()
    expect(parseCurl('wget https://example.com')).toBeNull()
  })

  it('解析简单 GET', () => {
    const r = parseCurl('curl https://api.example.com/users')
    expect(r).not.toBeNull()
    expect(r!.method).toBe('GET')
    expect(r!.path).toBe('https://api.example.com/users')
    expect(r!.request_spec.body.type).toBe('none')
  })

  it('解析 -X POST、-H、-d 与 JSON body', () => {
    const r = parseCurl(
      `curl -X POST 'https://api.example.com/login' \\
        -H 'Content-Type: application/json' \\
        -d '{"user":"a","pass":"b"}'`,
    )
    expect(r).not.toBeNull()
    expect(r!.method).toBe('POST')
    expect(r!.request_spec.headers).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: 'Content-Type', value: 'application/json', enabled: true }),
      ]),
    )
    expect(r!.request_spec.body.type).toBe('json')
    expect(r!.request_spec.body.raw).toContain('"user"')
  })

  it('有 body 无 -X 时默认 POST', () => {
    const r = parseCurl(`curl https://api.example.com/x -d 'hello'`)
    expect(r!.method).toBe('POST')
    expect(r!.request_spec.body.type).toBe('raw')
  })

  it('解析 -u basic auth', () => {
    const r = parseCurl('curl -u admin:secret https://localhost:8000/api')
    expect(r!.request_spec.auth).toEqual({
      type: 'basic',
      username: 'admin',
      password: 'secret',
    })
  })

  it('无 URL 返回 null', () => {
    expect(parseCurl('curl -X GET')).toBeNull()
  })

  it('支持 --url 与双引号转义', () => {
    const r = parseCurl('curl --url "https://example.com/a?q=\\"x\\""')
    expect(r!.path).toContain('https://example.com/a')
  })
})

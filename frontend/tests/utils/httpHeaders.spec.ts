import { describe, expect, it } from 'vitest'
import type { KvRow } from '@/types/apifox'
import {
  COMMON_HEADER_PRESETS,
  headerDefaultValue,
  rowsToText,
  suggestHeaderKeys,
  textToRows,
} from '@/utils/httpHeaders'

describe('headerDefaultValue', () => {
  it('按小写匹配预设默认值', () => {
    expect(headerDefaultValue('Content-Type')).toBe('application/json')
    expect(headerDefaultValue(' content-type ')).toBe('application/json')
    expect(headerDefaultValue('Authorization')).toBe('Bearer ')
  })

  it('未知或空返回空串', () => {
    expect(headerDefaultValue('X-Custom')).toBe('')
    expect(headerDefaultValue(null)).toBe('')
    expect(headerDefaultValue(undefined)).toBe('')
  })
})

describe('suggestHeaderKeys', () => {
  it('空查询返回全部常用 header', () => {
    expect(suggestHeaderKeys('').length).toBeGreaterThan(10)
    expect(suggestHeaderKeys(null).map((x) => x.value)).toContain('Accept')
  })

  it('按子串过滤', () => {
    const keys = suggestHeaderKeys('content').map((x) => x.value)
    expect(keys).toEqual(expect.arrayContaining(['Content-Type', 'Content-Length']))
    expect(keys.every((k) => k.toLowerCase().includes('content'))).toBe(true)
  })
})

describe('rowsToText / textToRows', () => {
  it('空输入互转', () => {
    expect(rowsToText(null)).toBe('')
    expect(rowsToText([])).toBe('')
    expect(textToRows(null)).toEqual([])
    expect(textToRows('')).toEqual([])
  })

  it('启用行与注释行互转', () => {
    const rows: KvRow[] = [
      { key: 'Accept', value: '*/*', enabled: true, desc: '', type: 'string' },
      { key: 'X-Debug', value: '1', enabled: false, desc: '', type: 'string' },
      { key: '', value: '', enabled: true, desc: '', type: 'string' },
    ]
    const text = rowsToText(rows)
    expect(text).toBe('Accept: */*\n// X-Debug: 1')
    const back = textToRows(text)
    expect(back).toEqual([
      expect.objectContaining({ key: 'Accept', value: '*/*', enabled: true }),
      expect.objectContaining({ key: 'X-Debug', value: '1', enabled: false }),
    ])
  })

  it('支持 # 注释与无冒号行', () => {
    const rows = textToRows('# Host: example.com\nBareToken')
    expect(rows[0]).toMatchObject({ key: 'Host', value: 'example.com', enabled: false })
    expect(rows[1]).toMatchObject({ key: 'BareToken', value: '', enabled: true })
  })

  it('COMMON_HEADER_PRESETS 非空', () => {
    expect(COMMON_HEADER_PRESETS.length).toBeGreaterThan(0)
  })
})

import { describe, expect, it } from 'vitest'
import { toAssertionItems } from '@/utils/assertionItems'

describe('toAssertionItems', () => {
  it('空输入返回空数组', () => {
    expect(toAssertionItems(null, null)).toEqual([])
    expect(toAssertionItems(undefined, undefined)).toEqual([])
  })

  it('声明式断言：带运算符时期望含运算符标签', () => {
    const items = toAssertionItems(
      [
        {
          passed: true,
          type: 'status_code',
          operator: 'eq',
          expected: 200,
          actual: 200,
        },
        {
          passed: false,
          type: 'json_path',
          operator: 'neq',
          expected: 'x',
          actual: 'x',
        },
      ],
      [],
    )
    expect(items[0]).toEqual({
      passed: true,
      label: '通过',
      message: '[状态码] 期望: 等于 200',
    })
    expect(items[1]!.message).toContain('[JSON路径]')
    expect(items[1]!.message).toContain('期望: 不等于 x')
    expect(items[1]!.message).toContain('实际: x')
    expect(items[1]!.label).toBe('失败')
  })

  it('exists 运算符不拼期望值', () => {
    const items = toAssertionItems(
      [{ passed: true, type: 'json_path', operator: 'exists', path: '$.id' }],
      [],
    )
    expect(items[0]!.message).toBe('[JSON路径] 期望: 存在')
  })

  it('无运算符时沿用 message，失败补期望/实际', () => {
    const items = toAssertionItems(
      [
        {
          passed: false,
          type: 'contains',
          message: 'body 不含 token',
          expected: 'token',
          actual: 'oops',
        },
      ],
      [],
    )
    expect(items[0]!.message).toContain('body 不含 token')
    expect(items[0]!.message).toContain('期望: token ｜ 实际: oops')
  })

  it('解析脚本断言 ✓/✗，忽略普通日志', () => {
    const items = toAssertionItems(
      [],
      ['info: start', '✓ status ok', '[login.js] ✗ token exists | missing', 'debug done'],
    )
    expect(items).toEqual([
      { passed: true, label: '通过', message: '[脚本] status ok' },
      { passed: false, label: '失败', message: '[脚本] token exists | missing' },
    ])
  })
})

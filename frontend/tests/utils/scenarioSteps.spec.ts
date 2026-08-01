import { describe, expect, it } from 'vitest'
import type { ScenarioEditorStep } from '@/types/apifox'
import { normalizeSteps, serializeStep } from '@/utils/scenarioSteps'

describe('normalizeSteps', () => {
  it('非数组返回空', () => {
    expect(normalizeSteps(null)).toEqual([])
    expect(normalizeSteps({})).toEqual([])
  })

  it('为步骤补 _uid，并规范化 http config', () => {
    const steps = normalizeSteps([
      {
        type: 'http',
        enabled: true,
        config: { method: 'POST', path: '/x' },
      },
    ])
    expect(steps).toHaveLength(1)
    expect(steps[0]!._uid).toMatch(/^s-\d+$/)
    expect(steps[0]!.config).toMatchObject({
      method: 'POST',
      path: '/x',
      assertions: [],
      extracts: [],
    })
    expect(
      (steps[0]!.config as { request_spec?: unknown } | null | undefined)?.request_spec,
    ).toBeTruthy()
  })

  it('if 步骤：抽出 else 到 elseChildren，缺 condition 时补默认', () => {
    const steps = normalizeSteps([
      {
        type: 'if',
        enabled: true,
        config: {},
        children: [
          { type: 'wait', wait_ms: 10, enabled: true },
          {
            type: 'else',
            enabled: true,
            children: [{ type: 'break', enabled: true }],
          },
        ],
      },
    ] as ScenarioEditorStep[])
    const ifStep = steps[0]!
    expect(ifStep.elseEnabled).toBe(true)
    expect(ifStep.children!.map((c) => c.type)).toEqual(['wait'])
    expect(ifStep.elseChildren!.map((c) => c.type)).toEqual(['break'])
    expect(ifStep.config).toEqual({
      condition: { left: '', operator: 'eq', right: '' },
    })
  })
})

describe('serializeStep', () => {
  it('if + elseEnabled 时把 else 写回 children', () => {
    const out = serializeStep({
      type: 'if',
      enabled: true,
      name: 'cond',
      config: { condition: { left: 'a', operator: 'eq', right: '1' } },
      children: [{ type: 'wait', wait_ms: 5, enabled: true, _uid: 1 }],
      elseEnabled: true,
      elseChildren: [{ type: 'continue', enabled: true, _uid: 2 }],
      _uid: 0,
    })
    expect(out.type).toBe('if')
    expect(out.children).toHaveLength(2)
    expect(out.children![0]!.type).toBe('wait')
    expect(out.children![1]!.type).toBe('else')
    expect(out.children![1]!.children![0]!.type).toBe('continue')
  })

  it('group/loop 递归序列化 children；其他类型 children 为空', () => {
    const group = serializeStep({
      type: 'group',
      name: 'g',
      enabled: true,
      children: [{ type: 'wait', wait_ms: 1, enabled: false, _uid: 1 }],
      _uid: 0,
    })
    expect(group.children).toHaveLength(1)
    expect(group.children![0]!.enabled).toBe(false)

    const wait = serializeStep({ type: 'wait', wait_ms: 9, enabled: true, _uid: 3 })
    expect(wait.children).toEqual([])
    expect(wait.wait_ms).toBe(9)
  })
})

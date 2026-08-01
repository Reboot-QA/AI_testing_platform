import { describe, expect, it } from 'vitest'
import {
  createCaseRefStep,
  createHttpStep,
  createStepByType,
  nextEditorUid,
} from '@/utils/scenarioStepFactory'

describe('nextEditorUid', () => {
  it('递增且为正整数', () => {
    const a = nextEditorUid()
    const b = nextEditorUid()
    expect(b).toBe(a + 1)
    expect(a).toBeGreaterThan(0)
  })
})

describe('createHttpStep', () => {
  it('默认 GET 空路径，并带 normalize 后的 request_spec', () => {
    const step = createHttpStep()
    expect(step.type).toBe('http')
    expect(step.enabled).toBe(true)
    expect(step.name).toBe('HTTP 请求')
    expect(step.config).toMatchObject({
      method: 'GET',
      path: '',
      server_name: null,
      assertions: [],
      extracts: [],
    })
    expect(
      (step.config as { request_spec?: unknown } | null | undefined)?.request_spec,
    ).toBeTruthy()
    expect(typeof step._uid).toBe('number')
  })

  it('覆盖字段生效', () => {
    const step = createHttpStep({
      name: '登录',
      method: 'POST',
      path: '/login',
      server_name: 'main',
    })
    expect(step.name).toBe('登录')
    expect(step.config).toMatchObject({
      name: '登录',
      method: 'POST',
      path: '/login',
      server_name: 'main',
    })
  })
})

describe('createCaseRefStep', () => {
  it('缺省未指定用例', () => {
    const step = createCaseRefStep()
    expect(step).toMatchObject({
      type: 'case',
      ref_case_id: null,
      enabled: true,
      case_name: '未指定用例',
    })
  })
})

describe('createStepByType', () => {
  it('http / case 走工厂', () => {
    expect(createStepByType('http')!.type).toBe('http')
    expect(createStepByType('case')!.type).toBe('case')
  })

  it('容器与控制流类型带默认 config', () => {
    expect(createStepByType('wait')).toMatchObject({ type: 'wait', wait_ms: 500 })
    expect(createStepByType('group')).toMatchObject({
      type: 'group',
      name: '分组',
      children: [],
    })
    expect(createStepByType('if')).toMatchObject({
      type: 'if',
      elseEnabled: false,
      elseChildren: [],
      config: { condition: { left: '', operator: 'eq', right: '' } },
    })
    expect(createStepByType('loop')!.config).toMatchObject({ mode: 'count', count: 1 })
    expect(createStepByType('db')!.config).toMatchObject({
      connection_id: null,
      sql: '',
      extracts: [],
    })
    expect(createStepByType('break')!.type).toBe('break')
    expect(createStepByType('continue')!.type).toBe('continue')
    expect(createStepByType('scenario')).toMatchObject({
      type: 'scenario',
      scenario_name: '未指定场景',
    })
  })

  it('导入类命令返回 null', () => {
    expect(createStepByType('import-case')).toBeNull()
    expect(createStepByType('import-endpoint')).toBeNull()
    expect(createStepByType('import-curl')).toBeNull()
  })
})

import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/types'
import {
  deriveEndpointProcessors,
  deriveProcessors,
  processorsToLegacy,
} from '@/utils/caseProcessors'

type Processor = Schemas['ProcessorRow']

/** 测试用最小 Processor：补齐 schema 必填字符串，业务字段用 overrides */
function proc(overrides: Partial<Processor> & Pick<Processor, 'kind'>): Processor {
  return {
    enabled: true,
    script_name: '',
    script_lang: '',
    content: '',
    sql: '',
    ...overrides,
  }
}

describe('deriveProcessors', () => {
  it('已有处理器时不覆盖', () => {
    const existing: Processor[] = [proc({ kind: 'script', script_id: 1 })]
    const f = {
      pre_processors: existing,
      post_processors: existing,
      pre_scripts: [{ script_id: 99, enabled: true }],
      assertions: [
        { type: 'status_code', path: '', operator: 'eq', expected: '200', enabled: true },
      ],
    }
    deriveProcessors(f)
    expect(f.pre_processors).toBe(existing)
    expect(f.post_processors).toBe(existing)
  })

  it('空处理器时按旧字段派生：前置脚本 + 断言→提取→后置脚本', () => {
    const f: {
      pre_scripts: { script_id: number; enabled: boolean }[]
      assertions: {
        type: string
        path: string
        operator: string
        expected: string
        enabled: boolean
      }[]
      extracts: {
        var_name: string
        source: string
        path: string
        scope: string
        enabled: boolean
      }[]
      post_scripts: { script_id: number }[]
      pre_processors?: Processor[]
      post_processors?: Processor[]
    } = {
      pre_scripts: [{ script_id: 1, enabled: false }],
      assertions: [
        { type: 'status_code', path: '', operator: 'eq', expected: '200', enabled: true },
      ],
      extracts: [
        {
          var_name: 'token',
          source: 'response_json',
          path: '$.token',
          scope: 'local',
          enabled: true,
        },
      ],
      post_scripts: [{ script_id: 2 }],
    }
    deriveProcessors(f)
    expect(f.pre_processors).toEqual([{ kind: 'script', script_id: 1, enabled: false }])
    expect(f.post_processors!.map((p) => p.kind)).toEqual(['assertion', 'extract', 'script'])
    expect(f.post_processors![2]).toEqual({ kind: 'script', script_id: 2, enabled: true })
  })

  it('缺省旧字段时派生为空数组', () => {
    const f: { pre_processors?: Processor[]; post_processors?: Processor[] } = {}
    deriveProcessors(f)
    expect(f.pre_processors).toEqual([])
    expect(f.post_processors).toEqual([])
  })
})

describe('deriveEndpointProcessors', () => {
  it('有 response_schema_id 时在断言后插入契约', () => {
    const f: {
      assertions: {
        type: string
        path: string
        operator: string
        expected: string
        enabled: boolean
      }[]
      extracts: {
        var_name: string
        source: string
        path: string
        scope: string
        enabled: boolean
      }[]
      response_schema_id: number
      contract_strict: boolean
      post_processors?: Processor[]
    } = {
      assertions: [
        { type: 'status_code', path: '', operator: 'eq', expected: '200', enabled: true },
      ],
      extracts: [
        {
          var_name: 'id',
          source: 'response_json',
          path: '$.id',
          scope: 'local',
          enabled: true,
        },
      ],
      response_schema_id: 7,
      contract_strict: true,
    }
    deriveEndpointProcessors(f)
    expect(f.post_processors!.map((p) => p.kind)).toEqual(['assertion', 'contract', 'extract'])
    expect(f.post_processors![1]).toMatchObject({
      kind: 'contract',
      response_schema_id: 7,
      contract_strict: true,
      enabled: true,
    })
  })

  it('已有 post_processors 时直接返回', () => {
    const post: Processor[] = [proc({ kind: 'wait', wait_ms: 100 })]
    const f = { post_processors: post, response_schema_id: 1 }
    deriveEndpointProcessors(f)
    expect(f.post_processors).toBe(post)
  })
})

describe('processorsToLegacy', () => {
  it('拆回旧字段并保留 inline / wait / contract', () => {
    const pre: Processor[] = [
      proc({ kind: 'script', script_id: 1 }),
      proc({
        kind: 'script_inline',
        content: 'pm.test()',
        script_lang: 'javascript',
      }),
      proc({ kind: 'wait', wait_ms: 200 }),
      proc({ kind: 'wait', wait_ms: 50, enabled: false }),
    ]
    const post: Processor[] = [
      proc({
        kind: 'assertion',
        type: 'status_code',
        path: '',
        operator: 'eq',
        expected: '200',
      }),
      proc({
        kind: 'extract',
        var_name: 't',
        source: 'response_json',
        path: '$.t',
        scope: 'local',
      }),
      proc({ kind: 'contract', response_schema_id: 9, contract_strict: true }),
      proc({ kind: 'script', script_id: 3, enabled: false }),
    ]
    const legacy = processorsToLegacy(pre, post)
    expect(legacy.pre_scripts).toEqual([{ script_id: 1, enabled: true }])
    expect(legacy.pre_inline).toEqual([{ content: 'pm.test()', lang: 'javascript', enabled: true }])
    expect(legacy.pre_waits).toEqual([200])
    expect(legacy.post_waits).toEqual([])
    expect(legacy.assertions).toHaveLength(1)
    expect(legacy.extracts).toHaveLength(1)
    expect(legacy.response_schema_id).toBe(9)
    expect(legacy.contract_strict).toBe(true)
    expect(legacy.post_scripts).toEqual([{ script_id: 3, enabled: false }])
  })
})

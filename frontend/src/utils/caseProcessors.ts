import type { Schemas } from '@/api/types'

type Processor = Schemas['ProcessorRow']

interface ProcessorFormFields {
  assertions?: Schemas['AssertionRow'][]
  extracts?: Schemas['ExtractRow'][]
  pre_scripts?: { script_id?: number | null; enabled?: boolean }[]
  post_scripts?: { script_id?: number | null; enabled?: boolean }[]
  pre_processors?: Processor[]
  post_processors?: Processor[]
}

/**
 * 存量用例（无处理器）由旧分列字段派生统一有序处理器，保持旧执行顺序：
 * 前置 = 前置脚本；后置 = 断言 → 提取 → 后置脚本。已有处理器则不动。
 * 在父组件加载用例后、计算脏检查快照前调用，避免时序不一致。
 */
export function deriveProcessors(f: ProcessorFormFields): void {
  if (!f.pre_processors?.length) {
    f.pre_processors = (f.pre_scripts || []).map(
      (s) =>
        ({
          kind: 'script',
          script_id: s.script_id ?? null,
          enabled: s.enabled ?? true,
        }) as Processor,
    )
  }
  if (!f.post_processors?.length) {
    f.post_processors = [
      ...(f.assertions || []).map(
        (a) =>
          ({
            kind: 'assertion',
            type: a.type,
            path: a.path,
            operator: a.operator,
            expected: a.expected,
            enabled: a.enabled,
          }) as Processor,
      ),
      ...(f.extracts || []).map(
        (e) =>
          ({
            kind: 'extract',
            var_name: e.var_name,
            source: e.source,
            path: e.path,
            scope: e.scope,
            enabled: e.enabled,
          }) as Processor,
      ),
      ...(f.post_scripts || []).map(
        (s) =>
          ({
            kind: 'script',
            script_id: s.script_id ?? null,
            enabled: s.enabled ?? true,
          }) as Processor,
      ),
    ]
  }
}

interface EndpointProcessorFields extends ProcessorFormFields {
  response_schema_id?: number | null
  contract_strict?: boolean
}

/** 接口级派生：后置含契约（断言 → 契约 → 提取 → 后置脚本）。 */
export function deriveEndpointProcessors(f: EndpointProcessorFields): void {
  if (!f.pre_processors?.length) {
    f.pre_processors = (f.pre_scripts || []).map(
      (s) =>
        ({
          kind: 'script',
          script_id: s.script_id ?? null,
          enabled: s.enabled ?? true,
        }) as Processor,
    )
  }
  if (f.post_processors?.length) return
  f.post_processors = [
    ...(f.assertions || []).map(
      (a) =>
        ({
          kind: 'assertion',
          type: a.type,
          path: a.path,
          operator: a.operator,
          expected: a.expected,
          enabled: a.enabled,
        }) as Processor,
    ),
    ...(f.response_schema_id
      ? [
          {
            kind: 'contract',
            response_schema_id: f.response_schema_id,
            contract_strict: !!f.contract_strict,
            enabled: true,
          } as Processor,
        ]
      : []),
    ...(f.extracts || []).map(
      (e) =>
        ({
          kind: 'extract',
          var_name: e.var_name,
          source: e.source,
          path: e.path,
          scope: e.scope,
          enabled: e.enabled,
        }) as Processor,
    ),
    ...(f.post_scripts || []).map(
      (s) =>
        ({
          kind: 'script',
          script_id: s.script_id ?? null,
          enabled: s.enabled ?? true,
        }) as Processor,
    ),
  ]
}

/** 把有序处理器拆回旧式字段（供 debug 直发等仍用旧管线的路径实时派生）。 */
export function processorsToLegacy(pre: Processor[], post: Processor[]) {
  const scripts = (arr: Processor[]) =>
    arr
      .filter((p) => p.kind === 'script')
      .map((p) => ({ script_id: p.script_id ?? null, enabled: p.enabled }))
  const contract = post.find((p) => p.kind === 'contract')
  return {
    pre_scripts: scripts(pre),
    post_scripts: scripts(post),
    assertions: post
      .filter((p) => p.kind === 'assertion')
      .map((p) => ({
        type: p.type,
        path: p.path,
        operator: p.operator,
        expected: p.expected,
        enabled: p.enabled,
      })),
    extracts: post
      .filter((p) => p.kind === 'extract')
      .map((p) => ({
        var_name: p.var_name,
        source: p.source,
        path: p.path,
        scope: p.scope,
        enabled: p.enabled,
      })),
    response_schema_id: contract?.response_schema_id ?? null,
    contract_strict: !!contract?.contract_strict,
  }
}

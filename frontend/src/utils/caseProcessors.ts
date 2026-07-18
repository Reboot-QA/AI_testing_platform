import type { Schemas } from '@/api/types'

type Processor = Schemas['ProcessorRow']

interface ProcessorFormFields {
  assertions?: Schemas['AssertionRow'][]
  extracts?: Schemas['ExtractRow'][]
  pre_scripts?: { script_id?: number | null; enabled?: boolean }[]
  post_scripts?: { script_id?: number | null; enabled?: boolean }[]
  pre_processors: Processor[]
  post_processors: Processor[]
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

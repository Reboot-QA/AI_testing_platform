// 套件项的分组视图：扁平有序的 items 按「接口」聚合展示（参考 Apifox 测试用例步骤区）。
// 数据契约不变——items 仍是扁平有序数组，sort_order = 数组下标；分组只是展示层的聚合。
import type { Schemas } from '@/api/types'
import type { SuiteEditorItem } from '@/types/apifox'

type ProjectCaseBrief = Schemas['ProjectCaseBrief']

export interface SuiteItemGroup {
  /** 分组唯一键：用例组为 'case:METHOD PATH'，场景组固定 'scenario' */
  key: string
  kind: 'case' | 'scenario'
  /** 接口名（查不到时退化为路径）；场景组为空 */
  name: string
  method: string
  path: string
  items: SuiteEditorItem[]
}

/** 用例项的分组键：同一接口下的用例聚成一组 */
function caseGroupKey(item: SuiteEditorItem): string {
  return `case:${item.endpoint_method} ${item.endpoint_path}`
}

/**
 * 按接口聚合套件项。
 * 组的先后 = 该组第一个项在 items 中的位置（首次出现顺序，保证稳定）；
 * 场景组恒排在所有用例组之后，与执行顺序规范化规则一致。
 */
export function buildSuiteItemGroups(
  items: SuiteEditorItem[],
  cases: ProjectCaseBrief[] = [],
): SuiteItemGroup[] {
  const endpointNameByCaseId = new Map(cases.map((c) => [c.id, c.endpoint_name]))
  const caseGroups: SuiteItemGroup[] = []
  const byKey = new Map<string, SuiteItemGroup>()
  const scenarioItems: SuiteEditorItem[] = []

  for (const item of items) {
    if (item.target_type === 'scenario') {
      scenarioItems.push(item)
      continue
    }
    const key = caseGroupKey(item)
    let group = byKey.get(key)
    if (!group) {
      group = {
        key,
        kind: 'case',
        name: '',
        method: item.endpoint_method,
        path: item.endpoint_path,
        items: [],
      }
      byKey.set(key, group)
      caseGroups.push(group)
    }
    group.items.push(item)
  }

  // 接口名取组内首个能查到的用例（用例被删除时查不到，退化为路径）
  for (const group of caseGroups) {
    for (const item of group.items) {
      const name = endpointNameByCaseId.get(item.target_id)
      if (name) {
        group.name = name
        break
      }
    }
    if (!group.name) group.name = group.path || '未知接口'
  }

  if (scenarioItems.length) {
    caseGroups.push({
      key: 'scenario',
      kind: 'scenario',
      name: '',
      method: '',
      path: '',
      items: scenarioItems,
    })
  }
  return caseGroups
}

/** 分组展开回扁平有序数组——执行顺序即视图从上到下的顺序 */
export function flattenSuiteItemGroups(groups: SuiteItemGroup[]): SuiteEditorItem[] {
  return groups.flatMap((g) => g.items)
}

/** 两个数组是否同序同项（按引用比较，用于避免无谓写回） */
export function sameOrder(a: SuiteEditorItem[], b: SuiteEditorItem[]): boolean {
  return a.length === b.length && a.every((it, i) => it === b[i])
}

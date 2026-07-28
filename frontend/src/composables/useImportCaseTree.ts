import { buildApiTree, type ApiTreeNode } from '@/composables/useApiTree'
import type { Schemas } from '@/api/types'

type ProjectCaseBrief = Schemas['ProjectCaseBrief']

export interface ImportTreeNode {
  key: string
  id: number
  type: 'folder' | 'endpoint' | 'root' | 'case' | 'scenario' | 'scenario-folder' | 'scenario-root' | 'suite' | 'suite-root'
  label: string
  method?: string
  path?: string
  folderId?: number | null
  endpointCount?: number
  caseCount?: number
  scenarioCount?: number
  suiteCount?: number
  endpointId?: number
  disabled?: boolean
  children?: ImportTreeNode[]
}

export type ImportCaseBrief = Pick<
  ProjectCaseBrief,
  'id' | 'name' | 'endpoint_id' | 'endpoint_method' | 'endpoint_name'
>

export type ImportScenarioBrief = Pick<Schemas['ScenarioBrief'], 'id' | 'name'>

/** 套件项需要接口路径直接回填（ProjectCaseBrief 不含 path，由弹窗从接口列表补齐） */
export type ImportSuiteCaseBrief = ImportCaseBrief & { endpoint_path: string }

export type ImportSuiteBrief = Pick<Schemas['SuiteBrief'], 'id' | 'name'>

export type ImportConfirmPayload =
  | { mode: 'import-endpoint' | 'import-debug'; endpointIds: number[] }
  | { mode: 'import-case'; cases: ImportCaseBrief[]; importAs: 'copy' | 'reference' }
  | { mode: 'pick-suite-item'; cases: ImportSuiteCaseBrief[]; scenarios: ImportScenarioBrief[] }
  | { mode: 'pick-schedule-case'; case: ImportSuiteCaseBrief }
  | { mode: 'pick-schedule-scenario'; scenario: ImportScenarioBrief }
  | { mode: 'pick-schedule-suite'; suite: ImportSuiteBrief }

function cloneApiNodes(nodes: ApiTreeNode[]): ImportTreeNode[] {
  return nodes.map((n) => ({
    ...n,
    children: n.children ? cloneApiNodes(n.children) : undefined,
  }))
}

/** 在接口树各 endpoint 下挂载用例子节点，并写入 caseCount */
export function attachCasesToTree(
  folders: Schemas['FolderOut'][],
  endpoints: Schemas['EndpointBrief'][],
  cases: ProjectCaseBrief[],
): ImportTreeNode[] {
  const byEndpoint = new Map<number, ProjectCaseBrief[]>()
  for (const c of cases) {
    const list = byEndpoint.get(c.endpoint_id) ?? []
    list.push(c)
    byEndpoint.set(c.endpoint_id, list)
  }

  const roots = cloneApiNodes(buildApiTree(folders, endpoints))

  function walk(nodes: ImportTreeNode[]) {
    for (const node of nodes) {
      if (node.type === 'endpoint') {
        const epCases = byEndpoint.get(node.id) ?? []
        node.caseCount = epCases.length
        node.children = epCases.map((c) => ({
          key: `c-${c.id}`,
          id: c.id,
          type: 'case' as const,
          label: c.name,
          endpointId: c.endpoint_id,
          method: c.endpoint_method,
        }))
      } else if (node.children?.length) {
        walk(node.children)
      }
    }
  }
  walk(roots)
  assignCaseCounts(roots)
  return roots
}

/** 汇总各目录/项目下的用例总数（endpoint 已在 walk 中写入 caseCount） */
function assignCaseCounts(nodes: ImportTreeNode[]): number {
  let total = 0
  for (const node of nodes) {
    if (node.type === 'endpoint') {
      total += node.caseCount ?? 0
    } else if (node.type === 'folder') {
      const count = assignCaseCounts(node.children ?? [])
      node.caseCount = count
      total += count
    }
  }
  return total
}

/** 场景分组根节点 key（与接口树根 'root' 并列，勾选时可整组级联） */
export const SCENARIO_ROOT_KEY = 'scenario-root'

/**
 * 构建「测试场景」分组节点：场景目录（扁平一层）→ 场景。
 * 未归档、以及 folder_id 指向已删除目录的场景，统一挂到「未分组」下，避免丢失。
 */
export function buildScenarioGroupNode(
  folders: Schemas['ScenarioFolderOut'][],
  scenarios: Schemas['ScenarioBrief'][],
): ImportTreeNode {
  const folderIds = new Set(folders.map((f) => f.id))
  const byFolder = new Map<number, ImportTreeNode[]>()
  const ungrouped: ImportTreeNode[] = []

  for (const s of scenarios) {
    const node: ImportTreeNode = { key: `s-${s.id}`, id: s.id, type: 'scenario', label: s.name }
    if (s.folder_id != null && folderIds.has(s.folder_id)) {
      const list = byFolder.get(s.folder_id) ?? []
      list.push(node)
      byFolder.set(s.folder_id, list)
    } else {
      ungrouped.push(node)
    }
  }

  const children: ImportTreeNode[] = folders.map((f) => {
    const kids = byFolder.get(f.id) ?? []
    return {
      key: `sf-${f.id}`,
      id: f.id,
      type: 'scenario-folder' as const,
      label: f.name,
      scenarioCount: kids.length,
      children: kids,
    }
  })
  if (ungrouped.length) {
    children.push({
      key: 'sf-none',
      id: 0,
      type: 'scenario-folder',
      label: '未分组',
      scenarioCount: ungrouped.length,
      children: ungrouped,
    })
  }

  return {
    key: SCENARIO_ROOT_KEY,
    id: 0,
    type: 'scenario-root',
    label: '测试场景',
    scenarioCount: scenarios.length,
    children,
  }
}

/** 测试套件分组根（扁平列表挂在根下） */
export const SUITE_ROOT_KEY = 'suite-root'

export function buildSuiteGroupNode(suites: Schemas['SuiteBrief'][]): ImportTreeNode {
  return {
    key: SUITE_ROOT_KEY,
    id: 0,
    type: 'suite-root',
    label: '测试套件',
    suiteCount: suites.length,
    children: suites.map((s) => ({
      key: `su-${s.id}`,
      id: s.id,
      type: 'suite' as const,
      label: s.name,
    })),
  }
}

export function applyImportTreeDisabled(nodes: ImportTreeNode[], _mode: 'endpoint' | 'case'): void {
  for (const node of nodes) {
    // 项目根/目录/接口均可勾选；提交时按 endpoint 或 case 叶子过滤
    node.disabled = false
    if (node.children?.length) applyImportTreeDisabled(node.children, _mode)
  }
}

export function filterImportTreeNode(value: string, data: ImportTreeNode): boolean {
  if (!value) return true
  const kw = value.trim().toLowerCase()
  if (!kw) return true
  if ((data.label || '').toLowerCase().includes(kw)) return true
  if ((data.path || '').toLowerCase().includes(kw)) return true
  if ((data.method || '').toLowerCase().includes(kw)) return true
  if (data.type === 'endpoint' && data.children?.length) {
    return data.children.some((c) => (c.label || '').toLowerCase().includes(kw))
  }
  return false
}

// 定时任务「执行目标」的树数据：按目标类型给出可单选的树（el-tree-select 用）。
// 树的构建直接复用导入弹窗那套（attachCasesToTree / buildScenarioGroupNode），
// 这里只做三件事：包一层可选性（非叶子 disabled）、补长短两种标签、key ↔ target_id 互转。
import type { Schemas } from '@/api/types'
import {
  attachCasesToTree,
  buildScenarioGroupNode,
  type ImportTreeNode,
} from '@/composables/useImportCaseTree'

export type ScheduleTargetType = 'case' | 'scenario' | 'suite'

/**
 * label = 收起后输入框显示的完整文本（带接口方法/路径，避免只看到用例名认不出是哪个接口）；
 * shortLabel = 树内节点显示的简洁文本（层级已提供上下文）。
 */
export interface ScheduleTreeNode extends Omit<ImportTreeNode, 'children' | 'type'> {
  /** 套件是扁平叶子，导入树里没有对应类型，这里补一个 */
  type: ImportTreeNode['type'] | 'suite'
  shortLabel: string
  children?: ScheduleTreeNode[]
}

export interface ScheduleTargetSource {
  folders: Schemas['FolderOut'][]
  endpoints: Schemas['EndpointBrief'][]
  cases: Schemas['ProjectCaseBrief'][]
  scenarioFolders: Schemas['ScenarioFolderOut'][]
  scenarios: Schemas['ScenarioBrief'][]
  suites: Schemas['SuiteBrief'][]
}

/** 各类型叶子的 key 前缀；与导入弹窗保持一致（用例 c- / 场景 s-），套件另起 su- */
const KEY_PREFIX: Record<ScheduleTargetType, string> = {
  case: 'c',
  scenario: 's',
  suite: 'su',
}

/** target_type + target_id → 树节点 key（编辑已有任务时回显用） */
export function targetToKey(type: ScheduleTargetType, id: number | null): string | null {
  return id == null ? null : `${KEY_PREFIX[type]}-${id}`
}

/** 树节点 key → target_id；key 形如 c-12 / s-3 / su-7 */
export function keyToTargetId(key: string | null): number | null {
  if (!key) return null
  const id = Number(key.slice(key.indexOf('-') + 1))
  return Number.isFinite(id) ? id : null
}

/**
 * 转换导入树 → 可单选的定时任务树：
 * 只有目标叶子可点，目录/接口/场景分组一律置灰；用例叶子补上「[方法] 路径 · 用例名」长标签。
 */
function toSelectableNodes(
  nodes: ImportTreeNode[],
  leafType: 'case' | 'scenario',
  endpointPath = '',
): ScheduleTreeNode[] {
  return nodes.map((node) => {
    const path = node.type === 'endpoint' ? node.path || '' : endpointPath
    const isLeaf = node.type === leafType
    const label =
      isLeaf && leafType === 'case'
        ? `[${node.method || 'GET'}] ${path} · ${node.label}`
        : node.label
    return {
      ...node,
      label,
      shortLabel: node.label,
      disabled: !isLeaf,
      children: node.children?.length
        ? toSelectableNodes(node.children, leafType, path)
        : undefined,
    }
  })
}

/** 按目标类型构建树：用例=目录/接口/用例三级，场景=目录/场景两级，套件=扁平 */
export function buildScheduleTargetTree(
  type: ScheduleTargetType,
  src: ScheduleTargetSource,
): ScheduleTreeNode[] {
  if (type === 'suite') {
    return src.suites.map((s) => ({
      key: `su-${s.id}`,
      id: s.id,
      type: 'suite' as const,
      label: s.name,
      shortLabel: s.name,
      disabled: false,
    }))
  }

  if (type === 'scenario') {
    // buildScenarioGroupNode 带一层「测试场景」总根，定时任务里多余，只取它的分组children
    const root = buildScenarioGroupNode(src.scenarioFolders, src.scenarios)
    return toSelectableNodes(root.children ?? [], 'scenario')
  }

  return toSelectableNodes(attachCasesToTree(src.folders, src.endpoints, src.cases), 'case')
}

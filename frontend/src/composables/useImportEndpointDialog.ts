import { computed, nextTick, ref, watch, type Ref } from 'vue'
import type { Id } from '@/api/request'
import { apifoxApi } from '@/api'
import { buildApiTree } from '@/composables/useApiTree'
import {
  applyImportTreeDisabled,
  attachCasesToTree,
  buildScenarioGroupNode,
  buildSuiteGroupNode,
  filterImportTreeNode,
  type ImportConfirmPayload,
  type ImportTreeNode,
} from '@/composables/useImportCaseTree'
import { useWorkspaceStore } from '@/stores/workspace'

export type ImportEndpointMode =
  | 'import-endpoint'
  | 'import-case'
  | 'import-debug'
  | 'pick-suite-item'
  | 'pick-suite-case'
  | 'pick-suite-scenario'
  | 'pick-schedule-case'
  | 'pick-schedule-scenario'
  | 'pick-schedule-suite'

type SchedulePickMode = 'pick-schedule-case' | 'pick-schedule-scenario' | 'pick-schedule-suite'

function isSchedulePickMode(mode: ImportEndpointMode): mode is SchedulePickMode {
  return (
    mode === 'pick-schedule-case' ||
    mode === 'pick-schedule-scenario' ||
    mode === 'pick-schedule-suite'
  )
}

type PickSuiteMode = 'pick-suite-item' | 'pick-suite-case' | 'pick-suite-scenario'

// 写成类型守卫，confirm() 的 else 分支才能正确收窄到 import-endpoint | import-debug
function isPickSuiteMode(mode: ImportEndpointMode): mode is PickSuiteMode {
  return mode === 'pick-suite-item' || mode === 'pick-suite-case' || mode === 'pick-suite-scenario'
}

export const MODE_META: Record<
  ImportEndpointMode,
  { title: string; searchPlaceholder: string; emptyText: string }
> = {
  'import-endpoint': {
    title: '从接口导入',
    searchPlaceholder: '搜索接口名 / 路径 / 文件夹',
    emptyText: '暂无接口',
  },
  'import-case': {
    title: '从单接口用例导入',
    searchPlaceholder: '搜索用例名 / 接口名 / 路径',
    emptyText: '暂无用例',
  },
  'import-debug': {
    title: '从接口调试用例导入',
    searchPlaceholder: '搜索接口名 / 路径 / 文件夹',
    emptyText: '暂无接口',
  },
  'pick-suite-item': {
    title: '添加用例 / 场景',
    searchPlaceholder: '搜索用例名 / 接口名 / 路径 / 场景名',
    emptyText: '暂无用例或场景',
  },
  'pick-suite-case': {
    title: '添加接口用例',
    searchPlaceholder: '搜索用例名 / 接口名 / 路径',
    emptyText: '暂无接口用例',
  },
  'pick-suite-scenario': {
    title: '添加测试场景',
    searchPlaceholder: '搜索场景名',
    emptyText: '暂无测试场景',
  },
  'pick-schedule-case': {
    title: '选择执行用例',
    searchPlaceholder: '搜索接口名 / 路径 / 文件夹',
    emptyText: '暂无用例',
  },
  'pick-schedule-scenario': {
    title: '选择执行场景',
    searchPlaceholder: '搜索场景名',
    emptyText: '暂无测试场景',
  },
  'pick-schedule-suite': {
    title: '选择执行套件',
    searchPlaceholder: '搜索套件名',
    emptyText: '暂无测试套件',
  },
}

type TreeExpose = {
  filter: (value: string) => void
  getCheckedKeys: (leafOnly?: boolean) => (string | number)[]
  setCheckedKeys: (keys: string[]) => void
}

type CaseMeta = {
  id: number
  name: string
  endpoint_id: number
  endpoint_method: string
  endpoint_name: string
  /** 由接口列表补齐（ProjectCaseBrief 不含 path），套件项直接回填展示 */
  endpoint_path: string
}

type ScenarioMeta = { id: number; name: string }

export function useImportEndpointDialog(
  projectId: Ref<Id>,
  emit: (payload: ImportConfirmPayload) => void,
) {
  const workspace = useWorkspaceStore()
  const visible = ref(false)
  const importMode = ref<ImportEndpointMode>('import-endpoint')
  const importAs = ref<'copy' | 'reference'>('reference')
  const loading = ref(false)
  const filterText = ref('')
  const treeData = ref<ImportTreeNode[]>([])
  const treeRef = ref<TreeExpose | null>(null)
  const checkedCount = ref(0)
  const caseMap = ref(new Map<number, CaseMeta>())
  const scenarioMap = ref(new Map<number, ScenarioMeta>())
  const suiteMap = ref(new Map<number, ScenarioMeta>())
  /** 勾了节点却一个可添加项都没选中（如勾了空接口/空目录），用于提示而非静默无反应 */
  const noPickableHint = ref(false)

  /** 是否需要在接口树下挂用例子节点 */
  const withCases = computed(
    () =>
      importMode.value === 'import-case' ||
      importMode.value === 'pick-suite-item' ||
      importMode.value === 'pick-suite-case' ||
      importMode.value === 'pick-schedule-case',
  )

  const projectName = computed(() => workspace.currentProjectName)
  const dialogTitle = computed(() => MODE_META[importMode.value].title)
  const searchPlaceholder = computed(() => MODE_META[importMode.value].searchPlaceholder)
  const emptyText = computed(() => MODE_META[importMode.value].emptyText)

  function filterNode(value: string, data: ImportTreeNode): boolean {
    return filterImportTreeNode(value, data)
  }

  watch(filterText, (v) => treeRef.value?.filter(v))

  /** 当前模式下哪种叶子可被采纳 */
  function isPickable(node: ImportTreeNode): boolean {
    if (importMode.value === 'pick-suite-case' || importMode.value === 'pick-schedule-case') {
      return node.type === 'case'
    }
    if (importMode.value === 'pick-suite-scenario' || importMode.value === 'pick-schedule-scenario') {
      return node.type === 'scenario'
    }
    if (importMode.value === 'pick-schedule-suite') return node.type === 'suite'
    if (importMode.value === 'pick-suite-item') {
      return node.type === 'case' || node.type === 'scenario'
    }
    if (importMode.value === 'import-case') return node.type === 'case'
    return node.type === 'endpoint'
  }

  /**
   * 从自有树数据推导选中的叶子，而不是读 el-tree 的 getCheckedNodes：
   * 后者只覆盖已渲染的节点，勾一个从未展开过的目录/分组会漏算。
   * 勾中的父节点向下传播到所有后代叶子。
   */
  function pickedLeaves(): ImportTreeNode[] {
    const keys = new Set(treeRef.value?.getCheckedKeys(false) ?? [])
    const out: ImportTreeNode[] = []
    const walk = (nodes: ImportTreeNode[], inherited: boolean) => {
      for (const node of nodes) {
        const checked = inherited || keys.has(node.key)
        if (node.children?.length) walk(node.children, checked)
        else if (checked && isPickable(node)) out.push(node)
      }
    }
    walk(treeData.value, false)
    return out
  }

  function syncCheckedCount() {
    checkedCount.value = pickedLeaves().length
    // 勾中了节点但没有任何可添加叶子（空接口/空目录），给出提示
    const anyChecked = (treeRef.value?.getCheckedKeys(false) ?? []).length > 0
    noPickableHint.value = checkedCount.value === 0 && anyChecked
  }

  /** 定时任务仅绑定单个目标：勾选叶子时清掉其它勾选项 */
  function onTreeCheck(data: ImportTreeNode) {
    if (!isSchedulePickMode(importMode.value)) {
      syncCheckedCount()
      return
    }
    const singleLeaf =
      (importMode.value === 'pick-schedule-case' && data.type === 'case') ||
      (importMode.value === 'pick-schedule-scenario' && data.type === 'scenario') ||
      (importMode.value === 'pick-schedule-suite' && data.type === 'suite')
    if (singleLeaf) treeRef.value?.setCheckedKeys([data.key])
    syncCheckedCount()
  }

  /** 全部移除：一键清空已勾选项（参考 apifox 导入弹窗） */
  function clearChecked() {
    treeRef.value?.setCheckedKeys([])
    checkedCount.value = 0
    noPickableHint.value = false
  }

  async function loadTree() {
    loading.value = true
    try {
      if (importMode.value === 'pick-suite-scenario' || importMode.value === 'pick-schedule-scenario') {
        const [scenarioFolders, scenarios] = await Promise.all([
          apifoxApi.listScenarioFolders(projectId.value),
          apifoxApi.listScenarios(projectId.value),
        ])
        scenarioMap.value = new Map(scenarios.map((s) => [s.id, { id: s.id, name: s.name }]))
        caseMap.value = new Map()
        suiteMap.value = new Map()
        treeData.value = [buildScenarioGroupNode(scenarioFolders, scenarios)]
        applyImportTreeDisabled(treeData.value, 'case')
        await nextTick()
        treeRef.value?.setCheckedKeys([])
        checkedCount.value = 0
        noPickableHint.value = false
        if (filterText.value) treeRef.value?.filter(filterText.value)
        return
      }

      if (importMode.value === 'pick-schedule-suite') {
        const suites = await apifoxApi.listSuites(projectId.value)
        suiteMap.value = new Map(suites.map((s) => [s.id, { id: s.id, name: s.name }]))
        caseMap.value = new Map()
        scenarioMap.value = new Map()
        treeData.value = [buildSuiteGroupNode(suites)]
        applyImportTreeDisabled(treeData.value, 'endpoint')
        await nextTick()
        treeRef.value?.setCheckedKeys([])
        checkedCount.value = 0
        noPickableHint.value = false
        if (filterText.value) treeRef.value?.filter(filterText.value)
        return
      }

      const [folders, endpoints] = await Promise.all([
        apifoxApi.listFolders(projectId.value),
        apifoxApi.listEndpoints(projectId.value),
      ])

      if (withCases.value) {
        const cases = await apifoxApi.listProjectCases(projectId.value)
        const pathById = new Map(endpoints.map((e) => [e.id, e.path]))
        caseMap.value = new Map(
          cases.map((c) => [
            c.id,
            {
              id: c.id,
              name: c.name,
              endpoint_id: c.endpoint_id,
              endpoint_method: c.endpoint_method,
              endpoint_name: c.endpoint_name,
              endpoint_path: pathById.get(c.endpoint_id) ?? '',
            },
          ]),
        )
        treeData.value = [
          {
            key: 'root',
            id: 0,
            type: 'root',
            label: projectName.value || '当前项目',
            endpointCount: endpoints.length,
            caseCount: cases.length,
            children: attachCasesToTree(folders, endpoints, cases),
          },
        ]
      } else {
        caseMap.value = new Map()
        treeData.value = [
          {
            key: 'root',
            id: 0,
            type: 'root',
            label: projectName.value || '当前项目',
            endpointCount: endpoints.length,
            children: buildApiTree(folders, endpoints) as ImportTreeNode[],
          },
        ]
      }

      if (importMode.value === 'pick-suite-item') {
        const [scenarioFolders, scenarios] = await Promise.all([
          apifoxApi.listScenarioFolders(projectId.value),
          apifoxApi.listScenarios(projectId.value),
        ])
        scenarioMap.value = new Map(scenarios.map((s) => [s.id, { id: s.id, name: s.name }]))
        treeData.value.push(buildScenarioGroupNode(scenarioFolders, scenarios))
      } else {
        scenarioMap.value = new Map()
      }

      applyImportTreeDisabled(treeData.value, withCases.value ? 'case' : 'endpoint')
      await nextTick()
      treeRef.value?.setCheckedKeys([])
      checkedCount.value = 0
      noPickableHint.value = false
      if (filterText.value) treeRef.value?.filter(filterText.value)
    } finally {
      loading.value = false
    }
  }

  function open(mode: ImportEndpointMode = 'import-endpoint') {
    importMode.value = mode
    importAs.value = 'reference'
    filterText.value = ''
    visible.value = true
    loadTree()
  }

  function onClosed() {
    filterText.value = ''
    treeData.value = []
    checkedCount.value = 0
    noPickableHint.value = false
    caseMap.value = new Map()
    scenarioMap.value = new Map()
    suiteMap.value = new Map()
  }

  function confirm() {
    if (importMode.value === 'pick-schedule-case') {
      const picked = pickedLeaves()
      const c = picked
        .map((n) => caseMap.value.get(n.id))
        .find((x): x is CaseMeta => !!x)
      if (!c) return
      emit({ mode: 'pick-schedule-case', case: c })
    } else if (importMode.value === 'pick-schedule-scenario') {
      const picked = pickedLeaves()
      const s = picked
        .map((n) => scenarioMap.value.get(n.id))
        .find((x): x is ScenarioMeta => !!x)
      if (!s) return
      emit({ mode: 'pick-schedule-scenario', scenario: s })
    } else if (importMode.value === 'pick-schedule-suite') {
      const picked = pickedLeaves()
      const su = picked
        .map((n) => suiteMap.value.get(n.id))
        .find((x): x is ScenarioMeta => !!x)
      if (!su) return
      emit({ mode: 'pick-schedule-suite', suite: su })
    } else if (isPickSuiteMode(importMode.value)) {
      const leaves = pickedLeaves()
      const cases = leaves
        .filter((n) => n.type === 'case')
        .map((n) => caseMap.value.get(n.id))
        .filter((c): c is CaseMeta => !!c)
      const scenarios = leaves
        .filter((n) => n.type === 'scenario')
        .map((n) => scenarioMap.value.get(n.id))
        .filter((s): s is ScenarioMeta => !!s)
      if (cases.length === 0 && scenarios.length === 0) return
      emit({ mode: 'pick-suite-item', cases, scenarios })
    } else if (importMode.value === 'import-case') {
      const cases = pickedLeaves()
        .map((n) => caseMap.value.get(n.id))
        .filter((c): c is CaseMeta => !!c)
      if (cases.length === 0) return
      emit({ mode: 'import-case', cases, importAs: importAs.value })
    } else {
      const ids = pickedLeaves().map((n) => n.id)
      if (ids.length === 0) return
      emit({ mode: importMode.value, endpointIds: ids })
    }
    visible.value = false
  }

  return {
    visible,
    importMode,
    importAs,
    loading,
    filterText,
    treeData,
    treeRef,
    checkedCount,
    noPickableHint,
    projectName,
    dialogTitle,
    searchPlaceholder,
    emptyText,
    filterNode,
    syncCheckedCount,
    onTreeCheck,
    clearChecked,
    open,
    onClosed,
    confirm,
  }
}

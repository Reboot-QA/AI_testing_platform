// 接口管理树的数据与交互（构建/搜索过滤/拖拽移动排序）；CRUD 与编辑器留在组件。
import { nextTick, ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'

type ApiFolder = Schemas['FolderOut']
type ApiEndpoint = Schemas['EndpointBrief']

export interface ApiTreeNode {
  key: string
  id: number
  type: 'folder' | 'endpoint' | 'root'
  label: string
  method?: string
  path?: string
  /** 接口所属目录（根级接口为 null） */
  folderId?: number | null
  endpointCount?: number
  casesStale?: boolean
  children?: ApiTreeNode[]
}

function assignEndpointCounts(nodes: ApiTreeNode[]): void {
  for (const node of nodes) {
    if (node.type !== 'folder' && node.type !== 'root') continue
    let count = 0
    for (const child of node.children || []) {
      if (child.type === 'endpoint') count++
      else {
        assignEndpointCounts([child])
        count += child.endpointCount ?? 0
      }
    }
    node.endpointCount = count
  }
}

/** 由文件夹 + 接口列表构建 el-tree 数据（接口树、导入选择器等共用） */
export function buildApiTree(folders: ApiFolder[], endpoints: ApiEndpoint[]): ApiTreeNode[] {
  const map: Record<number, ApiTreeNode> = {}
  folders.forEach((f) => {
    map[f.id] = { key: `f-${f.id}`, id: f.id, type: 'folder', label: f.name, children: [] }
  })
  const roots: ApiTreeNode[] = []
  folders.forEach((f) => {
    const node = map[f.id]!
    if (f.parent_id && map[f.parent_id]) map[f.parent_id]!.children!.push(node)
    else roots.push(node)
  })
  endpoints.forEach((e) => {
    const node: ApiTreeNode = {
      key: `e-${e.id}`,
      id: e.id,
      type: 'endpoint',
      label: e.name,
      method: e.method,
      path: e.path,
      folderId: e.folder_id ?? null,
      casesStale: e.cases_stale,
    }
    if (e.folder_id && map[e.folder_id]) map[e.folder_id]!.children!.push(node)
    else roots.push(node)
  })
  assignEndpointCounts(roots)
  return roots
}

/** el-tree 实例上用到的方法（避免拉全量 TreeInstance 类型） */
export interface ApiTreeExpose {
  filter: (value: string) => void
  getNode: (key: string | number) => { expand: () => void } | null
  setCurrentKey: (key: string | number | null) => void
}

interface ReorderFolderItem {
  id: number
  parent_id: number | null
  sort_order: number
}

interface ReorderEndpointItem {
  id: number
  folder_id: number | null
  sort_order: number
}

export interface ReloadTreeOptions {
  /** 刷新后额外展开该目录（及其祖先），用于新建接口/子目录后可见 */
  expandFolderId?: number | null
  /** 刷新后高亮该节点 key（如 e-123） */
  currentKey?: string | null
}

export interface UseApiTreeOptions {
  /**
   * 首屏自动展开前 N 层文件夹（depth 从 1 计，root 为第 1 层）：
   * depth ≤ N 的文件夹默认展开，更深的仍收起。0（默认）= 不自动展开。
   * 只在首次加载生效一次，之后尊重用户手动展开/收起。
   */
  autoExpandLevels?: number
}

export function useApiTree(
  pid: Ref<number | string | null | undefined>,
  options?: UseApiTreeOptions,
) {
  const autoExpandLevels = options?.autoExpandLevels ?? 0
  let autoExpandApplied = false
  const folders = ref<ApiFolder[]>([])
  const endpoints = ref<ApiEndpoint[]>([])
  const treeData = ref<ApiTreeNode[]>([])
  const treeRef = ref<ApiTreeExpose | null>(null)
  const filterText = ref('')
  /** 用户展开过的文件夹 key，reload 后还原，避免新建接口等操作把树收起 */
  const expandedKeys = ref<string[]>([])

  function buildTree(): void {
    treeData.value = buildApiTree(folders.value, endpoints.value)
  }

  function collectKeys(nodes: ApiTreeNode[], out: Set<string> = new Set()): Set<string> {
    for (const n of nodes) {
      out.add(n.key)
      if (n.children?.length) collectKeys(n.children, out)
    }
    return out
  }

  /** 收集深度 ≤ maxDepth 的文件夹 key（root 为第 1 层），用于首屏自动展开 */
  function collectFolderKeysWithinDepth(
    nodes: ApiTreeNode[],
    maxDepth: number,
    depth = 1,
    out: string[] = [],
  ): string[] {
    if (depth > maxDepth) return out
    for (const n of nodes) {
      if (n.type !== 'folder') continue
      out.push(n.key)
      collectFolderKeysWithinDepth(n.children || [], maxDepth, depth + 1, out)
    }
    return out
  }

  function collectDescendantKeys(node: ApiTreeNode): string[] {
    const keys: string[] = []
    for (const child of node.children || []) {
      keys.push(child.key, ...collectDescendantKeys(child))
    }
    return keys
  }

  function onNodeExpand(data: ApiTreeNode) {
    if (!expandedKeys.value.includes(data.key)) {
      expandedKeys.value = [...expandedKeys.value, data.key]
    }
  }

  function onNodeCollapse(data: ApiTreeNode) {
    const remove = new Set([data.key, ...collectDescendantKeys(data)])
    expandedKeys.value = expandedKeys.value.filter((k) => !remove.has(k))
  }

  /** 展开目录及其祖先（写入 expandedKeys，真正展开在 restoreExpanded） */
  function markFolderExpanded(folderId: number | null | undefined) {
    if (folderId == null) return
    let id: number | null = folderId
    while (id != null) {
      const key = `f-${id}`
      if (!expandedKeys.value.includes(key)) {
        expandedKeys.value = [...expandedKeys.value, key]
      }
      const folder = folders.value.find((f) => f.id === id)
      id = folder?.parent_id ?? null
    }
  }

  async function restoreExpanded(currentKey?: string | null): Promise<void> {
    await nextTick()
    const tree = treeRef.value
    if (!tree) return
    const valid = collectKeys(treeData.value)
    expandedKeys.value = expandedKeys.value.filter((k) => valid.has(k))
    for (const key of expandedKeys.value) {
      tree.getNode(key)?.expand()
    }
    if (currentKey && valid.has(currentKey)) {
      tree.setCurrentKey(currentKey)
    }
    if (filterText.value) tree.filter(filterText.value)
  }

  /**
   * 高亮指定接口节点（用于切换编辑器 tab 时让左侧树跟随）：
   * 展开其所在目录及祖先确保可见，再 setCurrentKey。传 null（如草稿 tab、无 tab）时清除高亮。
   */
  async function highlightEndpoint(id: number | null | undefined): Promise<void> {
    const tree = treeRef.value
    if (!tree) return
    if (id == null) {
      tree.setCurrentKey(null)
      return
    }
    const key = `e-${id}`
    if (!collectKeys(treeData.value).has(key)) {
      tree.setCurrentKey(null)
      return
    }
    const ep = endpoints.value.find((e) => e.id === id)
    markFolderExpanded(ep?.folder_id ?? null)
    await restoreExpanded(key)
  }

  async function reload(options?: ReloadTreeOptions): Promise<void> {
    const [fs, es] = await Promise.all([
      apifoxApi.listFolders(pid.value!),
      apifoxApi.listEndpoints(pid.value!),
    ])
    folders.value = fs
    endpoints.value = es
    if (options?.expandFolderId != null) markFolderExpanded(options.expandFolderId)
    buildTree()
    if (!autoExpandApplied && autoExpandLevels > 0) {
      autoExpandApplied = true
      const seed = collectFolderKeysWithinDepth(treeData.value, autoExpandLevels)
      const merged = new Set([...expandedKeys.value, ...seed])
      expandedKeys.value = [...merged]
    }
    await restoreExpanded(options?.currentKey)
  }

  function filterNode(value: string, data: ApiTreeNode): boolean {
    if (!value) return true
    const kw = value.trim().toLowerCase()
    if (!kw) return true
    if ((data.label || '').toLowerCase().includes(kw)) return true
    if ((data.path || '').toLowerCase().includes(kw)) return true
    if ((data.method || '').toLowerCase().includes(kw)) return true
    return false
  }

  watch(filterText, (v) => treeRef.value?.filter(v))

  function allowDrop(_dragNode: unknown, dropNode: { data: ApiTreeNode }, type: string): boolean {
    return !(type === 'inner' && dropNode.data.type === 'endpoint')
  }

  function buildReorderSnapshot(): {
    folders: ReorderFolderItem[]
    endpoints: ReorderEndpointItem[]
  } {
    const foldersOut: ReorderFolderItem[] = []
    const endpointsOut: ReorderEndpointItem[] = []
    const walk = (nodes: ApiTreeNode[], parentFolderId: number | null): void => {
      let fo = 0
      let eo = 0
      for (const n of nodes) {
        if (n.type === 'folder') {
          foldersOut.push({ id: n.id, parent_id: parentFolderId, sort_order: fo++ })
          walk(n.children || [], n.id)
        } else {
          endpointsOut.push({ id: n.id, folder_id: parentFolderId, sort_order: eo++ })
        }
      }
    }
    walk(treeData.value, null)
    return { folders: foldersOut, endpoints: endpointsOut }
  }

  async function onDrop(): Promise<void> {
    try {
      await apifoxApi.reorderTree(pid.value!, buildReorderSnapshot())
      ElMessage.success('已保存排序')
    } catch (e) {
      const err = e as { message?: string }
      ElMessage.error(err.message || '排序保存失败')
    }
    await reload()
  }

  return {
    treeData,
    treeRef,
    filterText,
    filterNode,
    allowDrop,
    onDrop,
    onNodeExpand,
    onNodeCollapse,
    highlightEndpoint,
    reload,
  }
}

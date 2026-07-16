// 接口管理树的数据与交互（构建/搜索过滤/拖拽移动排序）；CRUD 与编辑器留在组件。
import { ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'

type ApiFolder = Schemas['FolderOut']
type ApiEndpoint = Schemas['EndpointBrief']

export interface ApiTreeNode {
  key: string
  id: number
  type: 'folder' | 'endpoint'
  label: string
  method?: string
  children?: ApiTreeNode[]
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

export function useApiTree(pid: Ref<number | string | null | undefined>) {
  const folders = ref<ApiFolder[]>([])
  const endpoints = ref<ApiEndpoint[]>([])
  const treeData = ref<ApiTreeNode[]>([])
  const treeRef = ref<{ filter: (value: string) => void } | null>(null)
  const filterText = ref('')

  function buildTree(): void {
    const map: Record<number, ApiTreeNode> = {}
    folders.value.forEach((f) => {
      map[f.id] = { key: `f-${f.id}`, id: f.id, type: 'folder', label: f.name, children: [] }
    })
    const roots: ApiTreeNode[] = []
    folders.value.forEach((f) => {
      const node = map[f.id]!
      if (f.parent_id && map[f.parent_id]) map[f.parent_id]!.children!.push(node)
      else roots.push(node)
    })
    endpoints.value.forEach((e) => {
      const node: ApiTreeNode = {
        key: `e-${e.id}`,
        id: e.id,
        type: 'endpoint',
        label: e.name,
        method: e.method,
      }
      if (e.folder_id && map[e.folder_id]) map[e.folder_id]!.children!.push(node)
      else roots.push(node)
    })
    treeData.value = roots
  }

  async function reload(): Promise<void> {
    const [fs, es] = await Promise.all([
      apifoxApi.listFolders(pid.value!),
      apifoxApi.listEndpoints(pid.value!),
    ])
    folders.value = fs
    endpoints.value = es
    buildTree()
  }

  function filterNode(value: string, data: ApiTreeNode): boolean {
    return !value || (data.label || '').toLowerCase().includes(value.toLowerCase())
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

  return { treeData, treeRef, filterText, filterNode, allowDrop, onDrop, reload }
}

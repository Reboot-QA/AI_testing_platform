// 接口管理树的数据与交互（构建/搜索过滤/拖拽移动排序）；CRUD 与编辑器留在组件。
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { apifoxApi } from '@/api'

export function useApiTree(pid) {
  const folders = ref([])
  const endpoints = ref([])
  const treeData = ref([])
  const treeRef = ref()
  const filterText = ref('')

  function buildTree() {
    const map = {}
    folders.value.forEach((f) => {
      map[f.id] = { key: `f-${f.id}`, id: f.id, type: 'folder', label: f.name, children: [] }
    })
    const roots = []
    folders.value.forEach((f) => {
      const node = map[f.id]
      if (f.parent_id && map[f.parent_id]) map[f.parent_id].children.push(node)
      else roots.push(node)
    })
    endpoints.value.forEach((e) => {
      const node = { key: `e-${e.id}`, id: e.id, type: 'endpoint', label: e.name, method: e.method }
      if (e.folder_id && map[e.folder_id]) map[e.folder_id].children.push(node)
      else roots.push(node)
    })
    treeData.value = roots
  }

  async function reload() {
    const [fs, es] = await Promise.all([
      apifoxApi.listFolders(pid.value),
      apifoxApi.listEndpoints(pid.value),
    ])
    folders.value = fs
    endpoints.value = es
    buildTree()
  }

  function filterNode(value, data) {
    return !value || (data.label || '').toLowerCase().includes(value.toLowerCase())
  }
  watch(filterText, (v) => treeRef.value?.filter(v))

  // 接口不能作为容器：禁止拖到接口“内部”
  function allowDrop(dragNode, dropNode, type) {
    return !(type === 'inner' && dropNode.data.type === 'endpoint')
  }

  function buildReorderSnapshot() {
    const foldersOut = []
    const endpointsOut = []
    const walk = (nodes, parentFolderId) => {
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

  async function onDrop() {
    try {
      await apifoxApi.reorderTree(pid.value, buildReorderSnapshot())
      ElMessage.success('已保存排序')
    } catch (e) {
      ElMessage.error(e.message || '排序保存失败')
    }
    await reload()
  }

  return { treeData, treeRef, filterText, filterNode, allowDrop, onDrop, reload }
}

/** 导入「预览 & 勾选」树：由后端 ImportPreviewOut 构建 el-tree 数据，并从勾选态还原接口 key。 */

import type { Schemas } from '@/api/types'
import type { FolderOptionNode, ImportPreviewNode } from '@/types/apifox'

/** 非叶子节点 key 加前缀，避免与接口 key（"GET /users"）撞车 */
const ROOT_KEY = '#root'
const GROUP_KEY = '#group'
const folderKey = (name: string) => `#folder#${name}`

export { ROOT_KEY, GROUP_KEY }

export function buildImportPreviewTree(preview: Schemas['ImportPreviewOut']): ImportPreviewNode[] {
  const groups = preview.folders ?? []
  const children: ImportPreviewNode[] = []
  for (const group of groups) {
    const endpoints: ImportPreviewNode[] = (group.endpoints ?? []).map((e) => ({
      key: e.key,
      label: e.name,
      type: 'endpoint',
      method: e.method,
      path: e.path,
      exists: e.exists,
      changed: e.changed,
    }))
    // 无 tag 的接口不套目录，直接挂在「接口」分组下（导入时落在目标目录本身）
    if (!group.name) children.push(...endpoints)
    else {
      children.push({
        key: folderKey(group.name),
        label: group.name,
        type: 'folder',
        count: endpoints.length,
        children: endpoints,
      })
    }
  }
  return [
    {
      key: ROOT_KEY,
      label: preview.title || '导入数据',
      type: 'root',
      count: preview.total,
      children: [
        {
          key: GROUP_KEY,
          label: '接口',
          type: 'group',
          count: preview.total,
          children,
        },
      ],
    },
  ]
}

/** 全部接口 key（默认全选用） */
export function collectEndpointKeys(nodes: ImportPreviewNode[], out: string[] = []): string[] {
  for (const node of nodes) {
    if (node.type === 'endpoint') out.push(node.key)
    else if (node.children?.length) collectEndpointKeys(node.children, out)
  }
  return out
}

/**
 * 由勾选 key 集合推导选中的接口 key：勾中的父节点向下传播到所有后代。
 * 不用 el-tree 的 getCheckedNodes——它只覆盖已渲染节点，勾一个没展开过的目录会漏算。
 */
export function pickCheckedEndpointKeys(
  nodes: ImportPreviewNode[],
  checked: Set<string>,
  inherited = false,
  out: string[] = [],
): string[] {
  for (const node of nodes) {
    const on = inherited || checked.has(node.key)
    if (node.children?.length) pickCheckedEndpointKeys(node.children, checked, on, out)
    else if (on && node.type === 'endpoint') out.push(node.key)
  }
  return out
}

/** 关键字过滤：匹配接口名 / 路径 / 方法 / 目录名 */
export function filterPreviewNode(value: string, data: ImportPreviewNode): boolean {
  const kw = (value || '').trim().toLowerCase()
  if (!kw) return true
  return (
    data.label.toLowerCase().includes(kw) ||
    (data.path || '').toLowerCase().includes(kw) ||
    (data.method || '').toLowerCase().includes(kw)
  )
}

/** 目标目录下拉数据（只含接口目录，根目录由 clearable 的空值表示） */
export function buildFolderOptions(folders: Schemas['FolderOut'][]): FolderOptionNode[] {
  const map = new Map<number, FolderOptionNode>()
  folders.forEach((f) => map.set(f.id, { value: f.id, label: f.name, children: [] }))
  const roots: FolderOptionNode[] = []
  folders.forEach((f) => {
    const node = map.get(f.id)!
    const parent = f.parent_id != null ? map.get(f.parent_id) : undefined
    if (parent) parent.children!.push(node)
    else roots.push(node)
  })
  const prune = (nodes: FolderOptionNode[]) => {
    for (const n of nodes) {
      if (n.children?.length) prune(n.children)
      else delete n.children
    }
  }
  prune(roots)
  return roots
}

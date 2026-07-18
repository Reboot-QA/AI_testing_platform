import { computed, type ComputedRef } from 'vue'

import type { ApiMenuData, CatalogId } from '@/apifox2/components/ApiMenu'
import { CatalogType, MenuItemType } from '@/apifox2/enums'
import { isMenuFolder } from '@/apifox2/helpers'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

/** el-tree 使用的节点结构。 */
export interface MenuTreeNode {
  key: string
  /** 顶级目录节点用 catalogType；普通节点用 catalog。 */
  catalogType?: CatalogType
  catalog?: ApiMenuData
  isLeaf: boolean
  isTop: boolean
  children?: MenuTreeNode[]
}

const topMenus: CatalogType[] = [
  CatalogType.Overview,
  CatalogType.Http,
  CatalogType.Schema,
  CatalogType.Request,
  CatalogType.Recycle,
]

interface FlatNode {
  key: string
  catalog: ApiMenuData
  isLeaf: boolean
}

/** 将扁平列表按 parentId 组装为树。 */
function buildTree(flat: FlatNode[]): MenuTreeNode[] {
  const nodeMap = new Map<CatalogId, MenuTreeNode>()

  const nodes: MenuTreeNode[] = flat.map((item) => {
    const node: MenuTreeNode = {
      key: item.key,
      catalog: item.catalog,
      isLeaf: item.isLeaf,
      isTop: false,
      children: [],
    }
    nodeMap.set(item.catalog.id, node)
    return node
  })

  const roots: MenuTreeNode[] = []

  nodes.forEach((node) => {
    const parentId = node.catalog?.parentId
    if (parentId && nodeMap.has(parentId)) {
      nodeMap.get(parentId)!.children!.push(node)
    } else {
      roots.push(node)
    }
  })

  // 清理空 children，保证叶子无展开箭头。
  nodes.forEach((node) => {
    if (node.children && node.children.length === 0) {
      node.children = undefined
    }
  })

  return roots
}

function groupCatalogType(type: MenuItemType): CatalogType | null {
  switch (type) {
    case MenuItemType.ApiDetail:
    case MenuItemType.ApiDetailFolder:
    case MenuItemType.Doc:
      return CatalogType.Http
    case MenuItemType.ApiSchema:
    case MenuItemType.ApiSchemaFolder:
      return CatalogType.Schema
    case MenuItemType.HttpRequest:
    case MenuItemType.RequestFolder:
      return CatalogType.Request
    default:
      return null
  }
}

export interface UseMenuDataReturn {
  menuTree: ComputedRef<MenuTreeNode[]>
}

export function useMenuData(): UseMenuDataReturn {
  const store = useApifox2MenuStore()

  const menuTree = computed<MenuTreeNode[]>(() => {
    const menuRawList = store.menuRawList
    if (!menuRawList) return []

    const word = store.menuSearchWord
    const filtered = word ? menuRawList.filter(({ name }) => name.includes(word)) : menuRawList

    // 按类型分组。
    const grouped: Record<CatalogType, FlatNode[]> = {
      [CatalogType.Overview]: [],
      [CatalogType.Http]: [],
      [CatalogType.Schema]: [],
      [CatalogType.Request]: [],
      [CatalogType.Recycle]: [],
      [CatalogType.Markdown]: [],
    }

    filtered.forEach((catalog) => {
      const flat: FlatNode = {
        key: catalog.id,
        catalog,
        isLeaf: !isMenuFolder(catalog.type),
      }
      const groupType = groupCatalogType(catalog.type)
      if (groupType) {
        grouped[groupType].push(flat)
      }
    })

    return topMenus.map<MenuTreeNode>((catalogType) => {
      const children = buildTree(grouped[catalogType] ?? [])
      return {
        key: catalogType,
        catalogType,
        isLeaf: false,
        isTop: true,
        children: children.length ? children : undefined,
      }
    })
  })

  return { menuTree }
}

import { computed, type ComputedRef, type Ref, unref } from 'vue'

import type { ApiMenuData } from '@/apifox2/components/ApiMenu'
import { ROOT_CATALOG } from '@/apifox2/configs/static'
import { MenuItemType } from '@/apifox2/enums'
import { isMenuFolder } from '@/apifox2/helpers'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

export interface CatalogOption {
  value: string
  label: string
  disabled?: boolean
  children?: CatalogOption[]
}

interface FlatCatalog {
  value: string
  label: string
  disabled?: boolean
  parentId?: string
}

function buildCatalogTree(flat: FlatCatalog[]): CatalogOption[] {
  const map = new Map<string, CatalogOption>()
  const nodes: (CatalogOption & { parentId?: string })[] = flat.map((it) => {
    const node = { value: it.value, label: it.label, disabled: it.disabled, parentId: it.parentId }
    map.set(it.value, node)
    return node
  })
  const roots: CatalogOption[] = []
  nodes.forEach((node) => {
    if (node.parentId && map.has(node.parentId)) {
      const parent = map.get(node.parentId)!
      ;(parent.children ??= []).push(node)
    } else {
      roots.push(node)
    }
  })
  return roots
}

export interface UseCatalogParams {
  type?: Ref<MenuItemType | undefined> | MenuItemType
  exclued?: Ref<ApiMenuData['id'][] | undefined> | ApiMenuData['id'][]
}

export function useCatalog(params: UseCatalogParams): {
  catalogOptions: ComputedRef<CatalogOption[]>
} {
  const store = useApifox2MenuStore()

  const catalogOptions = computed<CatalogOption[]>(() => {
    const type = unref(params.type)
    const exclued = unref(params.exclued)

    const menuList = store.menuRawList
      ?.filter((it) => it.type === type && isMenuFolder(it.type))
      .map<FlatCatalog>((it) => ({
        value: it.id,
        label: it.name,
        disabled: exclued?.includes(it.id),
        parentId: it.parentId,
      }))

    return [
      { value: ROOT_CATALOG, label: '根目录' },
      ...(Array.isArray(menuList) ? buildCatalogTree(menuList) : []),
    ]
  })

  return { catalogOptions }
}

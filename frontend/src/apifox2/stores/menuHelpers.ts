import { defineStore } from 'pinia'
import { nanoid } from '@/apifox2/lib/nanoid'

import type { ApiMenuData } from '@/apifox2/components/ApiMenu'
import { apiDirectoryData, creator, recycleGroupData } from '@/apifox2/data/remote'
import { CatalogType } from '@/apifox2/enums'
import { getCatalogType, isMenuFolder } from '@/apifox2/helpers'
import type { RecycleCatalogType, RecycleData, RecycleDataItem } from '@/apifox2/types'
import { moveArrayItem } from '@/apifox2/utils'

interface MoveInfo {
  dragKey: ApiMenuData['id']
  dropKey: ApiMenuData['id']
  /** the drop position relative to the drop node, inside 0, top -1, bottom 1 */
  dropPosition: 0 | -1 | 1
}

interface State {
  menuRawList: ApiMenuData[] | undefined
  recyleRawData: RecycleData | undefined
  menuSearchWord: string | undefined
  apiDetailDisplay: 'name' | 'path'
}

/** 对应 Apifox-UI 的 contexts/menu-helpers。 */
export const useApifox2MenuStore = defineStore('apifox2Menu', {
  state: (): State => ({
    menuRawList: undefined,
    recyleRawData: undefined,
    menuSearchWord: undefined,
    apiDetailDisplay: 'name',
  }),

  actions: {
    /** 初始化菜单原始数据（对应 React 中 useEffect 的初始化）。 */
    init() {
      // 深拷贝，避免修改到共享的 mock 常量。
      this.menuRawList = structuredClone(apiDirectoryData)
      this.recyleRawData = structuredClone(recycleGroupData)
    },

    setMenuSearchWord(word: string | undefined) {
      this.menuSearchWord = word
    },

    setApiDetailDisplay(display: 'name' | 'path') {
      this.apiDetailDisplay = display
    },

    /** 添加一个新的菜单项到菜单列表中。 */
    addMenuItem(menuData: ApiMenuData) {
      if (!this.menuRawList) this.menuRawList = []
      this.menuRawList.push(menuData)
    },

    /** 从菜单列表中移除一个菜单项（连同子项），并进入回收站。 */
    removeMenuItem({ id }: Pick<ApiMenuData, 'id'>) {
      if (!this.menuRawList) return

      const kept: ApiMenuData[] = []

      for (const item of this.menuRawList) {
        const shouldRemove = item.id === id || item.parentId === id

        if (shouldRemove) {
          if (this.recyleRawData) {
            let catalogType = getCatalogType(item.type)

            if (catalogType === CatalogType.Markdown) {
              catalogType = CatalogType.Http
            }

            if (
              catalogType === CatalogType.Http ||
              catalogType === CatalogType.Schema ||
              catalogType === CatalogType.Request
            ) {
              const group = this.recyleRawData[catalogType]
              group.list = [
                { id: nanoid(6), expiredAt: '30天', creator, deletedItem: item },
                ...(group.list ?? []),
              ]
            }
          }
        } else {
          kept.push(item)
        }
      }

      this.menuRawList = kept
    },

    /** 更新一个菜单项的信息。 */
    updateMenuItem({ id, ...rest }: Partial<ApiMenuData> & Pick<ApiMenuData, 'id'>) {
      if (!this.menuRawList) return

      this.menuRawList = this.menuRawList.map((item) => {
        if (item.id === id) {
          return {
            ...item,
            ...rest,
            data: { ...item.data, ...rest.data, name: rest.name ?? item.name },
          } as ApiMenuData
        }
        return item
      })
    },

    /** 从回收站中恢复菜单项。 */
    restoreMenuItem({
      restoreId,
      catalogType,
    }: Partial<ApiMenuData> & {
      restoreId: RecycleDataItem['id']
      catalogType: RecycleCatalogType
    }) {
      if (!this.recyleRawData) return

      const group = this.recyleRawData[catalogType]

      group.list = group.list?.filter((li) => {
        const shouldRestore = li.id === restoreId

        if (shouldRestore) {
          if (!this.menuRawList) this.menuRawList = []
          this.menuRawList.push(li.deletedItem)
        }

        return !shouldRestore
      })
    },

    /** 移动菜单项。 */
    moveMenuItem({ dragKey, dropKey, dropPosition }: MoveInfo) {
      if (!this.menuRawList) return

      const list = this.menuRawList

      const dragMenuIdx = list.findIndex((item) => item.id === dragKey)
      const dropMenuIdx = list.findIndex((item) => item.id === dropKey)
      const dragMenu = dragMenuIdx >= 0 ? list[dragMenuIdx] : null
      const dropMenu = dropMenuIdx >= 0 ? list[dropMenuIdx] : null

      if (dragMenu && dropMenu) {
        if (isMenuFolder(dropMenu.type) && dropPosition === 0) {
          list[dragMenuIdx].parentId = dropMenu.id
          moveArrayItem(list, dragMenuIdx, dropMenuIdx + 1)
        } else if (dropPosition === 1) {
          if (dragMenu.parentId !== dropMenu.parentId) {
            list[dragMenuIdx].parentId = dropMenu.parentId
            moveArrayItem(list, dragMenuIdx, dropMenuIdx + 1)
          } else {
            moveArrayItem(list, dragMenuIdx, dropMenuIdx + 1)
          }
        }
      }
    },
  },
})

import { defineStore } from 'pinia'

import type { ApiTabItem, EditStatus } from '@/apifox2/components/ApiTab'
import { initialActiveTabKey, initialTabItems } from '@/apifox2/data/remote'

interface State {
  /** 当前在 Tabs 中打开的所有页签。 */
  tabItems: ApiTabItem[]
  /** 当前激活的页签。 */
  activeTabKey: ApiTabItem['key'] | undefined
  /** 上一次被激活的页签。 */
  lastActiveTabKey: ApiTabItem['key'] | undefined
}

/** 对应 Apifox-UI 的 contexts/menu-tab-settings（含 useMenuTabHelpers）。 */
export const useApifox2TabStore = defineStore('apifox2Tab', {
  state: (): State => ({
    tabItems: [],
    activeTabKey: undefined,
    lastActiveTabKey: undefined,
  }),

  actions: {
    init() {
      this.tabItems = structuredClone(initialTabItems)
      this.activeTabKey = initialActiveTabKey
    },

    /** 激活指定的页签。 */
    activeTabItem(payload: Pick<ApiTabItem, 'key'>) {
      this.lastActiveTabKey = this.activeTabKey

      if (this.tabItems.length > 0) {
        this.activeTabKey = payload.key
      }
    },

    /** 获取指定的页签项。 */
    getTabItem(payload: Pick<ApiTabItem, 'key'>): ApiTabItem | undefined {
      return this.tabItems.find((item) => item.key === payload.key)
    },

    /** 添加新的页签。 */
    addTabItem(
      payload: ApiTabItem,
      config?: { autoActive?: boolean; replaceTab?: ApiTabItem['key'] },
    ) {
      const { autoActive = true, replaceTab } = config ?? {}

      const isSameTabPresent = this.tabItems.some((item) => item.key === payload.key)

      if (isSameTabPresent) {
        throw new Error('已存在相同的页签。')
      } else {
        if (replaceTab) {
          this.tabItems = this.tabItems.map((it) => (it.key === replaceTab ? payload : it))
        } else {
          this.tabItems = [...this.tabItems, payload]
        }

        if (autoActive) {
          this.activeTabItem({ key: payload.key })
        }
      }
    },

    /** 移除页签。 */
    removeTabItem(payload: Pick<ApiTabItem, 'key'>) {
      const newItems = this.tabItems.filter((item) => item.key !== payload.key)

      if (this.activeTabKey === payload.key) {
        this.activeTabKey = undefined

        const validTabKey =
          this.lastActiveTabKey &&
          newItems.findIndex((item) => item.key === this.lastActiveTabKey) !== -1

        if (validTabKey && this.lastActiveTabKey) {
          // activeTabItem 依赖 tabItems.length，故先更新列表。
          this.tabItems = newItems
          this.activeTabItem({ key: this.lastActiveTabKey })
          return
        } else {
          this.lastActiveTabKey = undefined

          const lastTabKey = newItems[newItems.length - 1]?.key

          if (lastTabKey) {
            this.tabItems = newItems
            this.activeTabItem({ key: lastTabKey })
            return
          }
        }
      }

      this.tabItems = newItems
    },

    /** 移除所有页签。 */
    removeAllTabItems() {
      this.activeTabKey = undefined
      this.tabItems = []
    },

    /** 移除所有页签，除了当前激活的页签。 */
    removeOtherTabItems() {
      if (this.activeTabKey) {
        this.tabItems = this.tabItems.filter((item) => item.key === this.activeTabKey)
      }
    },

    setTabItemEditStatus(payload: Pick<ApiTabItem, 'key'>, editStatus: EditStatus) {
      this.tabItems = this.tabItems.map((item) => {
        if (item.key === payload.key) {
          return { ...item, data: { ...item.data, editStatus } }
        }
        return item
      })
    },
  },
})

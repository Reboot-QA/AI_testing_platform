import { inject, provide, type InjectionKey } from 'vue'

import type { ApiTabItem } from '@/apifox2/components/ApiTab'

/** 对应 Apifox-UI 的 ApiTab/TabContentContext。 */
interface TabContentContextData {
  tabData: ApiTabItem
}

const KEY: InjectionKey<TabContentContextData> = Symbol('apifox2-tab-content')

export function provideTabContent(tabData: ApiTabItem) {
  provide(KEY, { tabData })
}

export function useTabContentContext(): TabContentContextData {
  const ctx = inject(KEY)
  if (!ctx) {
    throw new Error('useTabContentContext 必须在 provideTabContent 之下使用')
  }
  return ctx
}

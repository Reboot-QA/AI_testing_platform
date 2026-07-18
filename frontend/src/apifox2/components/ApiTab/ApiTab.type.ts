import type { TabContentType } from '@/apifox2/types'

import type { PageTabStatus } from './ApiTab.enum'

export type EditStatus = 'changed' | 'saved'

export interface ApiTabItem {
  key: string
  label?: string
  /** 页签内容类型。 */
  contentType: TabContentType
  /** 页签附加数据。 */
  data?: Record<string, unknown> & {
    editStatus?: EditStatus
    tabStatus?: PageTabStatus
  }
}

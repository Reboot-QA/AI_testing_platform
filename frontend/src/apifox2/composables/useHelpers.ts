import { nanoid } from '@/apifox2/lib/nanoid'

import { PageTabStatus } from '@/apifox2/components/ApiTab/ApiTab.enum'
import type { ApiTabItem } from '@/apifox2/components/ApiTab/ApiTab.type'
import { API_MENU_CONFIG } from '@/apifox2/configs/static'
import { CatalogType, MenuItemType } from '@/apifox2/enums'
import { useApifox2TabStore } from '@/apifox2/stores/menuTab'

type CreateConfig = { autoActive?: boolean; replaceTab?: ApiTabItem['key'] }

/** 对应 Apifox-UI 的 hooks/useHelpers。 */
export function useHelpers() {
  const tabStore = useApifox2TabStore()

  const createApiDetails = (payload?: Partial<ApiTabItem>, config?: CreateConfig) => {
    const { newLabel } = API_MENU_CONFIG[CatalogType.Http]

    tabStore.addTabItem(
      {
        ...payload,
        key: nanoid(6),
        label: newLabel,
        contentType: MenuItemType.ApiDetail,
        data: { tabStatus: PageTabStatus.Create },
      },
      config,
    )
  }

  const createApiRequest = (payload?: Partial<ApiTabItem>, config?: CreateConfig) => {
    const { newLabel } = API_MENU_CONFIG[CatalogType.Request]

    tabStore.addTabItem(
      {
        ...payload,
        key: nanoid(6),
        label: newLabel,
        contentType: MenuItemType.HttpRequest,
        data: { tabStatus: PageTabStatus.Create },
      },
      config,
    )
  }

  const createDoc = (payload?: Partial<ApiTabItem>, config?: CreateConfig) => {
    tabStore.addTabItem(
      {
        ...payload,
        key: nanoid(6),
        label: '新建 Markdown',
        contentType: MenuItemType.Doc,
        data: { tabStatus: PageTabStatus.Create },
      },
      config,
    )
  }

  const createApiSchema = (payload?: Partial<ApiTabItem>, config?: CreateConfig) => {
    const { newLabel } = API_MENU_CONFIG[CatalogType.Schema]

    tabStore.addTabItem(
      {
        ...payload,
        key: nanoid(6),
        label: newLabel,
        contentType: MenuItemType.ApiSchema,
        data: { tabStatus: PageTabStatus.Create },
      },
      config,
    )
  }

  const createTabItem = (t: MenuItemType) => {
    switch (t) {
      case MenuItemType.ApiDetail:
        createApiDetails()
        break
      case MenuItemType.HttpRequest:
        createApiRequest()
        break
      case MenuItemType.Doc:
        createDoc()
        break
      case MenuItemType.ApiSchema:
        createApiSchema()
        break
    }
  }

  return {
    createApiDetails,
    createApiRequest,
    createDoc,
    createApiSchema,
    createTabItem,
  }
}

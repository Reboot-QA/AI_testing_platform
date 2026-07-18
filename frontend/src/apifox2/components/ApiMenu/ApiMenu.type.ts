import type { MenuItemType } from '@/apifox2/enums'
import type { ApiDetails, ApiDoc, ApiFolder, ApiSchema } from '@/apifox2/types'

export interface ApiMenuBase {
  id: CatalogId
  parentId?: ApiMenuBase['id']
  name: string
  type: MenuItemType
}

interface ApiMenuInterface extends ApiMenuBase {
  type: MenuItemType.ApiDetail
  data?: ApiDetails
}

interface ApiMenuInterfaceFolder extends ApiMenuBase {
  type: MenuItemType.ApiDetailFolder
  data?: ApiFolder
}

interface ApiMenuDoc extends ApiMenuBase {
  type: MenuItemType.Doc
  data?: ApiDoc
}

interface ApiMenuSchema extends ApiMenuBase {
  type: MenuItemType.ApiSchema | MenuItemType.ApiSchemaFolder
  data?: ApiSchema
}

interface ApiMenuRequest extends ApiMenuBase {
  type: MenuItemType.HttpRequest | MenuItemType.RequestFolder
  data?: ApiDetails
}

export type CatalogId = string

export type ApiMenuData =
  ApiMenuInterface | ApiMenuSchema | ApiMenuDoc | ApiMenuRequest | ApiMenuInterfaceFolder

/**
 * 树节点数据。Element Plus 的 el-tree 需要 { id, label, children } 结构，
 * 这里用与 antd 语义对齐的自定义结构承载。
 */
export interface CatalogDataNode {
  key: string
  title?: string
  isLeaf?: boolean
  customData: {
    catalog: ApiMenuData
  }
  children?: CatalogDataNode[]
}

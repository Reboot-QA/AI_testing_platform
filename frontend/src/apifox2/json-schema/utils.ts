import type { ApiMenuData } from '@/apifox2/components/ApiMenu'
import { MenuItemType } from '@/apifox2/enums'

import { INDENT, KEY_ITEMS, KEY_PROPERTIES, SchemaType, SEPARATOR } from './constants'
import type { FieldPath, JsonSchema } from './types'

/** 轻量 lodash.get 替代：按路径数组读取嵌套值。 */
export function getByPath(obj: any, path: FieldPath[]): any {
  let cur: any = obj
  for (const key of path) {
    if (cur == null) return undefined
    cur = cur[key]
  }
  return cur
}

/** 轻量 lodash.set 替代：按路径数组写入嵌套值（原地）。 */
export function setByPath(obj: any, path: FieldPath[], value: any): void {
  if (path.length === 0) return
  let cur: any = obj
  for (let i = 0; i < path.length - 1; i++) {
    const key = path[i]
    if (cur[key] == null) {
      // 下一段是数字则建数组，否则建对象。
      cur[key] = /^\d+$/.test(String(path[i + 1])) ? [] : {}
    }
    cur = cur[key]
  }
  cur[path[path.length - 1]] = value
}

/**
 * 递归解析 JsonSchema，将所有可展开的节点的字段路径作为 key。
 */
export function getAllExpandedKeys(
  jsonSchema: JsonSchema,
  path: FieldPath[] = [],
  keys: string[] = [],
): string[] {
  if (jsonSchema.type === SchemaType.Object) {
    if (keys.length === 0) {
      keys.push('') // <-- 根节点
    }

    jsonSchema.properties?.forEach((js, i) => {
      const newPath = [...path, KEY_PROPERTIES, `${i}`]
      keys.push(newPath.join(SEPARATOR))
      getAllExpandedKeys(js, newPath, keys)
    })
  } else if (jsonSchema.type === SchemaType.Array) {
    const newPath = [...path, KEY_ITEMS]
    keys.push(newPath.join(SEPARATOR))
    getAllExpandedKeys(jsonSchema.items, newPath, keys)
  }

  return keys
}

/** 根据 Schema 中字段的路径，获取到该字段的层级。 */
export function getNodeLevelInfo(fieldPath: FieldPath[]): { level: number; indentWidth: number } {
  const level = fieldPath.filter(
    (pathName) => pathName === KEY_PROPERTIES || pathName === KEY_ITEMS,
  ).length

  const indentWidth = level * INDENT

  return { level, indentWidth }
}

export function getRefJsonSchema(
  menuRawList: ApiMenuData[],
  modelId: string,
): JsonSchema | undefined {
  const menuData = menuRawList.find(({ id }) => id === modelId)

  const jsonSchema =
    menuData?.type === MenuItemType.ApiSchema ? menuData.data?.jsonSchema : undefined

  return jsonSchema
}

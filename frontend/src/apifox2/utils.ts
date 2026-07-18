import type { AnyType, UnsafeAny } from '@/apifox2/types'

export function getPageTitle(title?: string): string {
  const mainTitle = 'Apifox UI'

  return title ? `${title} - ${mainTitle}` : mainTitle
}

/** 检查传入的值是否为简单的 JS 对象。 */
export function isPureObject(value: AnyType): value is Record<string, UnsafeAny> {
  return Object.prototype.toString.call(value) === '[object Object]'
}

/**
 * 深拷贝。用于克隆可能是 Vue reactive 代理的数据。
 * structuredClone 无法克隆 Proxy（会抛 DataCloneError），本项目数据均为 JSON 可序列化结构，
 * 故用 JSON 深拷贝，天然会读穿 reactive 代理为普通对象。
 */
export function deepClone<T>(value: T): T {
  if (value === undefined || value === null) return value
  return JSON.parse(JSON.stringify(value)) as T
}

/** 移动数组元素。 */
export function moveArrayItem<T>(arr: T[], fromIndex: number, toIndex: number) {
  // 先删除原位置上的元素。
  const element = arr.splice(fromIndex, 1)[0]

  // 然后在指定位置插入该元素。
  arr.splice(toIndex, 0, element)
}

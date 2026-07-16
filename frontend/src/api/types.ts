// 便捷别名：各 api 模块引用如 Schemas['ProjectOut']，类型全部由 schema.d.ts 工具生成。
import type { components, paths } from './schema'

export type Schemas = components['schemas']
export type { paths }

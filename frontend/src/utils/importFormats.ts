/** 导入数据源格式的展示元数据（设置页卡片 + 弹窗下拉共用） */

import type { ImportSourceFormat } from '@/types/apifox'

export interface ImportFormatMeta {
  key: ImportSourceFormat
  label: string
  abbr: string
  tone: string
  hint: string
}

export const IMPORT_FORMATS: ImportFormatMeta[] = [
  {
    key: 'openapi',
    label: 'OpenAPI/Swagger',
    abbr: 'OA',
    tone: 'green',
    hint: '支持导入 OpenAPI 3.0、3.1 或 Swagger 2.0 数据格式的 JSON 或 YAML 文件。',
  },
  {
    key: 'postman',
    label: 'Postman',
    abbr: 'PM',
    tone: 'orange',
    hint: '点击这里了解如何从 Postman 导出数据。',
  },
  {
    key: 'curl',
    label: 'cURL',
    abbr: 'CL',
    tone: 'blue',
    hint: '粘贴完整 cURL 命令即可导入为接口（自动识别 method / URL / Header / Body）。',
  },
  {
    key: 'apifox',
    label: 'Apifox',
    abbr: 'AF',
    tone: 'brand',
    hint: '',
  },
  {
    key: 'jmeter',
    label: 'JMeter',
    abbr: 'JM',
    tone: 'red',
    hint: '支持 .jmx 数据格式。',
  },
]

export function findImportFormat(key: ImportSourceFormat): ImportFormatMeta {
  return IMPORT_FORMATS.find((f) => f.key === key) ?? IMPORT_FORMATS[0]
}

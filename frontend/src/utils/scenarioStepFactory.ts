// 场景步骤「新建」工厂：顶层「添加步骤」与容器（分组/条件/循环）内联添加共用同一套构造逻辑，
// 保证不管从哪个入口新增，步骤形状（config 默认值、_uid）完全一致。
import type { Schemas } from '@/api/types'
import type { RequestSpec, ScenarioAddStepCommand, ScenarioEditorStep } from '@/types/apifox'
import { emptySpec, normalizeSpec } from '@/utils/apifoxSpec'

let _seq = 0

/** 新建步骤的自增 _uid（数字，与加载态的 `s-N` 字符串不冲突） */
export function nextEditorUid(): number {
  return ++_seq
}

export type HttpStepOverrides = Partial<{
  name: string
  method: string
  path: string
  server_name: string | null
  request_spec: RequestSpec
  assertions: Schemas['AssertionRow'][]
  extracts: Schemas['ExtractRow'][]
}>

export function createHttpStep(over: HttpStepOverrides = {}): ScenarioEditorStep {
  return {
    type: 'http',
    enabled: true,
    name: over.name || 'HTTP 请求',
    _uid: nextEditorUid(),
    config: {
      name: over.name || '',
      method: over.method || 'GET',
      path: over.path || '',
      server_name: over.server_name || null,
      // 统一归一化请求结构，两个导入路径与空步骤保持一致的形状
      request_spec: normalizeSpec(over.request_spec || emptySpec()),
      assertions: over.assertions || [],
      extracts: over.extracts || [],
    },
  }
}

export function createCaseRefStep(over: Partial<ScenarioEditorStep> = {}): ScenarioEditorStep {
  return {
    type: 'case',
    ref_case_id: over.ref_case_id ?? null,
    enabled: true,
    case_name: over.case_name || '未指定用例',
    ...(over.endpoint_method ? { endpoint_method: over.endpoint_method } : {}),
    _uid: nextEditorUid(),
  }
}

/** 按类型新建步骤；导入类命令（import-*）需走对话框，不在此处理，返回 null */
export function createStepByType(type: ScenarioAddStepCommand): ScenarioEditorStep | null {
  if (type === 'http') return createHttpStep()
  if (type === 'case') return createCaseRefStep()
  const uid = nextEditorUid()
  switch (type) {
    case 'scenario':
      return {
        type: 'scenario',
        ref_scenario_id: null,
        enabled: true,
        scenario_name: '未指定场景',
        _uid: uid,
      }
    case 'wait':
      return { type: 'wait', wait_ms: 500, enabled: true, _uid: uid }
    case 'group':
      return { type: 'group', name: '分组', enabled: true, children: [], _uid: uid }
    case 'if':
      return {
        type: 'if',
        enabled: true,
        _uid: uid,
        config: { condition: { left: '', operator: 'eq', right: '' } },
        children: [],
        elseEnabled: false,
        elseChildren: [],
      }
    case 'loop':
      return {
        type: 'loop',
        enabled: true,
        _uid: uid,
        children: [],
        config: {
          mode: 'count',
          count: 1,
          list_var: '',
          item_var: 'item',
          index_var: 'index',
          max_iterations: 10,
          condition: { left: '', operator: 'eq', right: '' },
        },
      }
    case 'db':
      return {
        type: 'db',
        enabled: true,
        name: '数据库操作',
        _uid: uid,
        config: { connection_id: null, sql: '', extracts: [] },
      }
    case 'break':
    case 'continue':
      return { type, enabled: true, _uid: uid }
    default:
      return null
  }
}

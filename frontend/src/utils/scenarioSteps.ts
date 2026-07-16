// 场景步骤在「后端契约树」与「前端工作态」之间的双向变换。
// 加载：if 的 else 子步骤拆成 elseEnabled/elseChildren（两个独立拖放区）；http 步骤补全 request_spec。
// 保存：把工作态还原回后端嵌套树。ScenarioPanel 与 scenarioTabs store 共用。
import { normalizeSpec } from '@/utils/apifoxSpec'

const MAX_STEP_DEPTH = 50

export function normalizeSteps(steps: any[]): any[] {
  return (steps || []).map(normalizeStep)
}

function normalizeStep(s: any): any {
  const node = { ...s }
  if (s.type === 'if') {
    const kids = normalizeSteps(s.children)
    const elseStep = kids.find((k) => k.type === 'else')
    node.children = kids.filter((k) => k.type !== 'else')
    node.elseEnabled = !!elseStep
    node.elseChildren = elseStep ? elseStep.children || [] : []
    if (!node.config?.condition)
      node.config = { condition: { left: '', operator: 'eq', right: '' } }
  } else if (s.type === 'http') {
    const c = s.config || {}
    node.config = {
      ...c,
      request_spec: normalizeSpec(c.request_spec),
      assertions: c.assertions || [],
      extracts: c.extracts || [],
    }
  } else {
    node.children = normalizeSteps(s.children)
  }
  return node
}

function leafStep(overrides: any): any {
  return {
    type: overrides.type,
    ref_case_id: overrides.ref_case_id ?? null,
    ref_scenario_id: overrides.ref_scenario_id ?? null,
    wait_ms: overrides.wait_ms ?? null,
    config: overrides.config ?? null,
    name: overrides.name ?? null,
    enabled: overrides.enabled !== false,
    children: overrides.children || [],
  }
}

export function serializeStep(s: any, depth = 0): any {
  const deep = depth < MAX_STEP_DEPTH
  // 条件(if)：then=children，elseEnabled 时把 elseChildren 包成一个 else 子步骤（还原后端嵌套树）
  if (s.type === 'if') {
    const children = deep ? (s.children || []).map((c: any) => serializeStep(c, depth + 1)) : []
    if (s.elseEnabled) {
      const elseChildren = deep
        ? (s.elseChildren || []).map((c: any) => serializeStep(c, depth + 1))
        : []
      children.push(leafStep({ type: 'else', children: elseChildren }))
    }
    return leafStep({ type: 'if', config: s.config, name: s.name, enabled: s.enabled, children })
  }
  const hasBody = s.type === 'group' || s.type === 'loop'
  const children =
    hasBody && deep ? (s.children || []).map((c: any) => serializeStep(c, depth + 1)) : []
  return leafStep({ ...s, children })
}

// 场景步骤在「后端契约树」与「前端工作态」之间的双向变换。
import type { ScenarioEditorStep } from '@/types/apifox'
import type { Schemas } from '@/api/types'
import { normalizeSpec } from '@/utils/apifoxSpec'

const MAX_STEP_DEPTH = 50
let stepUidSeq = 0

const nextStepUid = (): string => `s-${stepUidSeq++}`

export function normalizeSteps(steps: unknown): ScenarioEditorStep[] {
  if (!Array.isArray(steps)) return []
  return steps.map((step) => normalizeStep(step as ScenarioEditorStep))
}

function normalizeStep(step: ScenarioEditorStep): ScenarioEditorStep {
  const node: ScenarioEditorStep = { ...step, _uid: step._uid ?? nextStepUid() }
  if (step.type === 'if') {
    const children = normalizeSteps(step.children)
    const elseStep = children.find((child) => child.type === 'else')
    const config = (step.config ?? {}) as Record<string, unknown>
    node.children = children.filter((child) => child.type !== 'else')
    node.elseEnabled = Boolean(elseStep)
    node.elseChildren = elseStep?.children ?? []
    node.config = config.condition ? config : { condition: { left: '', operator: 'eq', right: '' } }
  } else if (step.type === 'http') {
    const config = (step.config ?? {}) as Record<string, unknown>
    node.config = {
      ...config,
      request_spec: normalizeSpec(config.request_spec),
      assertions: Array.isArray(config.assertions) ? config.assertions : [],
      extracts: Array.isArray(config.extracts) ? config.extracts : [],
    }
  } else {
    node.children = normalizeSteps(step.children)
  }
  return node
}

type SerializedStepOverrides = Omit<Partial<ScenarioEditorStep>, 'children'> & {
  type: string
  children?: Schemas['StepIn'][]
}

function leafStep(overrides: SerializedStepOverrides): Schemas['StepIn'] {
  return {
    type: overrides.type,
    ref_case_id: overrides.ref_case_id ?? null,
    ref_scenario_id: overrides.ref_scenario_id ?? null,
    wait_ms: overrides.wait_ms ?? null,
    config: overrides.config == null ? null : { ...overrides.config },
    name: overrides.name ?? null,
    enabled: overrides.enabled !== false,
    children: overrides.children ?? [],
  }
}

export function serializeStep(step: ScenarioEditorStep, depth = 0): Schemas['StepIn'] {
  const deep = depth < MAX_STEP_DEPTH
  if (step.type === 'if') {
    const children = deep
      ? (step.children ?? []).map((child) => serializeStep(child, depth + 1))
      : []
    if (step.elseEnabled) {
      const elseChildren = deep
        ? (step.elseChildren ?? []).map((child) => serializeStep(child, depth + 1))
        : []
      children.push(leafStep({ type: 'else', children: elseChildren }))
    }
    return leafStep({
      type: 'if',
      config: step.config,
      name: step.name,
      enabled: step.enabled,
      children,
    })
  }
  const hasBody = step.type === 'group' || step.type === 'loop'
  const children =
    hasBody && deep ? (step.children ?? []).map((child) => serializeStep(child, depth + 1)) : []
  return leafStep({ ...step, children })
}

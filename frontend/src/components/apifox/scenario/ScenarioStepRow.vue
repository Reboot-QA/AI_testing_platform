<template>
  <div>
    <div
      class="step-row"
      :class="{ active: selection.uid === row._uid, disabled: row.enabled === false }"
      @click.stop="selection.uid = row._uid ?? null"
    >
      <el-icon class="drag-handle" title="拖拽排序/移动"><Rank /></el-icon>
      <span class="idx">{{ index + 1 }}</span>
      <el-checkbox v-model="row.enabled" @click.stop />
      <el-tag size="small" :type="typeTag">{{ typeLabel }}</el-tag>
      <span class="step-name">{{ displayName }}</span>
      <el-button link type="danger" size="small" @click.stop="$emit('remove')">移除</el-button>
    </div>

    <div v-if="row.type === 'group'" class="group-body">
      <VueDraggable
        v-model="children"
        :group="{ name: 'scenario-steps' }"
        handle=".drag-handle"
        :animation="150"
        ghost-class="ax-drag-ghost"
        class="group-drop"
        :class="{ 'group-drop--empty': children.length === 0 }"
      >
        <ScenarioStepRow
          v-for="(child, i) in children"
          :key="child._uid"
          :row="child"
          :index="i"
          :cases="cases"
          :scenarios="scenarios"
          :current-scenario-id="currentScenarioId"
          :selection="selection"
          @remove="children.splice(i, 1)"
          @add="(cmd, list) => emit('add', cmd, list)"
        />
      </VueDraggable>
      <div class="child-add">
        <span class="child-add-text">拖入或</span>
        <ScenarioAddStepMenu compact @command="(cmd) => emit('add', cmd, children)" />
      </div>
    </div>

    <div v-else-if="row.type === 'if'" class="group-body">
      <div class="branch-label">Then（条件成立）</div>
      <VueDraggable
        v-model="children"
        :group="{ name: 'scenario-steps' }"
        handle=".drag-handle"
        :animation="150"
        ghost-class="ax-drag-ghost"
        class="group-drop"
        :class="{ 'group-drop--empty': children.length === 0 }"
      >
        <ScenarioStepRow
          v-for="(child, i) in children"
          :key="child._uid"
          :row="child"
          :index="i"
          :cases="cases"
          :scenarios="scenarios"
          :current-scenario-id="currentScenarioId"
          :selection="selection"
          @remove="children.splice(i, 1)"
          @add="(cmd, list) => emit('add', cmd, list)"
        />
      </VueDraggable>
      <div class="child-add">
        <span class="child-add-text">拖入或</span>
        <ScenarioAddStepMenu compact @command="(cmd) => emit('add', cmd, children)" />
      </div>

      <template v-if="row.elseEnabled">
        <div class="branch-label">Else（条件不成立）</div>
        <VueDraggable
          v-model="elseChildren"
          :group="{ name: 'scenario-steps' }"
          handle=".drag-handle"
          :animation="150"
          ghost-class="ax-drag-ghost"
          class="group-drop"
          :class="{ 'group-drop--empty': elseChildren.length === 0 }"
        >
          <ScenarioStepRow
            v-for="(child, i) in elseChildren"
            :key="child._uid"
            :row="child"
            :index="i"
            :cases="cases"
            :scenarios="scenarios"
            :current-scenario-id="currentScenarioId"
            :selection="selection"
            @remove="elseChildren.splice(i, 1)"
            @add="(cmd, list) => emit('add', cmd, list)"
          />
        </VueDraggable>
        <div class="child-add">
          <span class="child-add-text">拖入或</span>
          <ScenarioAddStepMenu compact @command="(cmd) => emit('add', cmd, elseChildren)" />
        </div>
      </template>
    </div>

    <div v-else-if="row.type === 'loop'" class="group-body">
      <div class="branch-label">循环体</div>
      <VueDraggable
        v-model="children"
        :group="{ name: 'scenario-steps' }"
        handle=".drag-handle"
        :animation="150"
        ghost-class="ax-drag-ghost"
        class="group-drop"
        :class="{ 'group-drop--empty': children.length === 0 }"
      >
        <ScenarioStepRow
          v-for="(child, i) in children"
          :key="child._uid"
          :row="child"
          :index="i"
          :cases="cases"
          :scenarios="scenarios"
          :current-scenario-id="currentScenarioId"
          :selection="selection"
          @remove="children.splice(i, 1)"
          @add="(cmd, list) => emit('add', cmd, list)"
        />
      </VueDraggable>
      <div class="child-add">
        <span class="child-add-text">拖入或</span>
        <ScenarioAddStepMenu compact @command="(cmd) => emit('add', cmd, children)" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import type { Schemas } from '@/api/types'
import type {
  HttpStepConfig,
  ScenarioAddStepCommand,
  ScenarioEditorStep,
  ScenarioStepSelection,
} from '@/types/apifox'
import {
  ensureElseChildren,
  ensureIfConfig,
  ensureLoopConfig,
  ensureStepChildren,
} from '@/types/apifox'
import ScenarioAddStepMenu from '@/components/apifox/scenario/ScenarioAddStepMenu.vue'

defineOptions({ name: 'ScenarioStepRow' })

type ProjectCaseBrief = Schemas['ProjectCaseBrief']
type ScenarioBrief = Schemas['ScenarioBrief']

withDefaults(
  defineProps<{
    index?: number
    cases?: ProjectCaseBrief[]
    scenarios?: ScenarioBrief[]
    currentScenarioId?: number | null
  }>(),
  {
    index: 0,
    cases: () => [],
    scenarios: () => [],
    currentScenarioId: null,
  },
)
const row = defineModel<ScenarioEditorStep>('row', { required: true })
const selection = defineModel<ScenarioStepSelection>('selection', { required: true })

// add：容器内联「添加步骤」，把命令与目标子列表冒泡给 ScenarioStepsEditor 统一新建（递归层层转发）
const emit = defineEmits<{
  remove: []
  add: [ScenarioAddStepCommand, ScenarioEditorStep[]]
}>()

// 拖动结束时 VueDraggable 会整体赋一个新数组；这里原地 splice 回原数组，
// 保持数组引用稳定（内联「添加步骤」记下的落点、外部持有的引用都不会失效）
const children = computed({
  get: () => ensureStepChildren(row.value),
  set: (value: ScenarioEditorStep[]) => {
    const list = ensureStepChildren(row.value)
    list.splice(0, list.length, ...value)
  },
})

const elseChildren = computed({
  get: () => ensureElseChildren(row.value),
  set: (value: ScenarioEditorStep[]) => {
    const list = ensureElseChildren(row.value)
    list.splice(0, list.length, ...value)
  },
})

const typeLabel = computed(
  () =>
    ({
      case: '用例',
      wait: '等待',
      scenario: '子场景',
      group: '分组',
      if: '条件',
      loop: '循环',
      break: '跳出循环',
      continue: '跳过本轮',
      db: '数据库',
      http: 'HTTP',
    })[row.value.type] || row.value.type,
)
const typeTag = computed(
  () =>
    ({
      case: 'success',
      wait: 'warning',
      scenario: 'info',
      group: 'primary',
      if: 'danger',
      loop: 'warning',
      break: 'danger',
      continue: 'info',
      db: 'primary',
      http: 'success',
    })[row.value.type] || 'info',
)

const displayName = computed(() => {
  const value = row.value
  if (value.type === 'if') {
    const c = ensureIfConfig(value).condition
    return `如果 ${c.left || '?'} ${c.operator || 'eq'} ${c.operator === 'exists' ? '' : (c.right ?? '')}`.trim()
  }
  if (value.type === 'loop') {
    const c = ensureLoopConfig(value)
    if (c.mode === 'list') return `遍历 ${c.list_var || '?'}`
    if (c.mode === 'while')
      return `当 ${c.condition?.left || '?'} ${c.condition?.operator || ''} … 时循环`
    return `循环 ${c.count ?? '?'} 次`
  }
  if (value.type === 'break') return '跳出循环'
  if (value.type === 'continue') return '跳过本轮'
  if (value.type === 'http') {
    const c = value.config as HttpStepConfig | undefined
    return `[${c?.method || 'GET'}] ${c?.path || value.name || 'HTTP'}`.trim()
  }
  if (value.name) return value.name
  if (value.type === 'case') {
    const prefix = value.endpoint_method ? `[${value.endpoint_method}] ` : ''
    return `${prefix}${value.case_name || `用例#${value.ref_case_id}`}`
  }
  if (value.type === 'wait') return `等待 ${value.wait_ms} ms`
  if (value.type === 'group') return `分组（${value.children?.length || 0}）`
  return value.scenario_name || `场景#${value.ref_scenario_id}`
})
</script>

<style scoped>
.step-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  margin-bottom: var(--ax-space-1);
  padding: var(--ax-space-1) var(--ax-space-1-5);
  border-radius: 4px;
  cursor: pointer;
  font-size: var(--ax-text-caption-size);
  line-height: var(--ax-leading-compact);
}

.step-row:hover {
  background: var(--ax-bg-hover);
}

.step-row.active {
  background: var(--ax-bg-active);
}

.step-row.disabled .step-name {
  color: var(--ax-text-placeholder);
  text-decoration: line-through;
}

.drag-handle {
  flex-shrink: 0;
  font-size: var(--ax-text-body-sm-size);
  cursor: grab;
  color: var(--ax-text-placeholder);
}

.drag-handle:active {
  cursor: grabbing;
}

.idx {
  flex-shrink: 0;
  width: 18px;
  font-size: var(--ax-text-caption-size);
  font-variant-numeric: tabular-nums;
  color: var(--ax-text-placeholder);
  text-align: right;
}

.step-row :deep(.el-checkbox) {
  height: auto;
  margin-right: 0;
}

.step-row :deep(.el-tag) {
  flex-shrink: 0;
  height: 20px;
  padding: 0 var(--ax-space-1-5);
  font-size: var(--ax-text-caption-size);
  line-height: 18px;
}

.step-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-text-caption-size);
  font-weight: 400;
  color: var(--ax-text);
}

.step-row :deep(.el-button.is-link) {
  flex-shrink: 0;
  padding: 0 var(--ax-space-1);
  font-size: var(--ax-text-caption-size);
  height: auto;
}

.group-body {
  margin-left: var(--ax-space-5);
  border-left: 2px solid var(--ax-border);
  padding-left: var(--ax-space-2);
}

.group-drop {
  min-height: 8px;
}

.group-drop--empty {
  min-height: 20px;
}

/* Apifox 同款：容器体末尾常驻虚线占位，既是拖入提示也是内联「添加步骤」入口 */
.child-add {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ax-space-1);
  margin-bottom: var(--ax-space-1);
  padding: var(--ax-space-1) var(--ax-space-1-5);
  border: 1px dashed var(--ax-border);
  border-radius: var(--ax-radius);
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-caption-size);
  line-height: var(--ax-leading-compact);
  transition: border-color var(--ax-transition);
}

.child-add:hover {
  border-color: var(--color-blue-6);
}

.branch-label {
  font-size: var(--ax-text-caption-size);
  font-weight: 600;
  line-height: var(--ax-leading-compact);
  color: var(--ax-text-secondary);
  margin: var(--ax-space-1) 0 var(--ax-space-0-5);
}
</style>

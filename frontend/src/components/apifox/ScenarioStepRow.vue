<template>
  <div>
    <div
      class="step-row"
      :class="{ active: selection.uid === row._uid, disabled: row.enabled === false }"
      @click.stop="selection.uid = row._uid"
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
        v-model="row.children"
        :group="{ name: 'scenario-steps' }"
        handle=".drag-handle"
        :animation="150"
        class="group-drop"
      >
        <ScenarioStepRow
          v-for="(child, i) in row.children"
          :key="child._uid"
          :row="child"
          :index="i"
          :cases="cases"
          :scenarios="scenarios"
          :current-scenario-id="currentScenarioId"
          :selection="selection"
          @remove="row.children.splice(i, 1)"
        />
      </VueDraggable>
      <div v-if="row.children.length === 0" class="group-empty">拖步骤到此分组内</div>
    </div>

    <div v-else-if="row.type === 'if'" class="group-body">
      <div class="branch-label">Then（条件成立）</div>
      <VueDraggable
        v-model="row.children"
        :group="{ name: 'scenario-steps' }"
        handle=".drag-handle"
        :animation="150"
        class="group-drop"
      >
        <ScenarioStepRow
          v-for="(child, i) in row.children"
          :key="child._uid"
          :row="child"
          :index="i"
          :cases="cases"
          :scenarios="scenarios"
          :current-scenario-id="currentScenarioId"
          :selection="selection"
          @remove="row.children.splice(i, 1)"
        />
      </VueDraggable>
      <div v-if="row.children.length === 0" class="group-empty">拖步骤到 Then 分支</div>

      <template v-if="row.elseEnabled">
        <div class="branch-label">Else（条件不成立）</div>
        <VueDraggable
          v-model="row.elseChildren"
          :group="{ name: 'scenario-steps' }"
          handle=".drag-handle"
          :animation="150"
          class="group-drop"
        >
          <ScenarioStepRow
            v-for="(child, i) in row.elseChildren"
            :key="child._uid"
            :row="child"
            :index="i"
            :cases="cases"
            :scenarios="scenarios"
            :current-scenario-id="currentScenarioId"
            :selection="selection"
            @remove="row.elseChildren.splice(i, 1)"
          />
        </VueDraggable>
        <div v-if="row.elseChildren.length === 0" class="group-empty">拖步骤到 Else 分支</div>
      </template>
    </div>

    <div v-else-if="row.type === 'loop'" class="group-body">
      <div class="branch-label">循环体</div>
      <VueDraggable
        v-model="row.children"
        :group="{ name: 'scenario-steps' }"
        handle=".drag-handle"
        :animation="150"
        class="group-drop"
      >
        <ScenarioStepRow
          v-for="(child, i) in row.children"
          :key="child._uid"
          :row="child"
          :index="i"
          :cases="cases"
          :scenarios="scenarios"
          :current-scenario-id="currentScenarioId"
          :selection="selection"
          @remove="row.children.splice(i, 1)"
        />
      </VueDraggable>
      <div v-if="row.children.length === 0" class="group-empty">拖步骤到循环体内</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'

defineOptions({ name: 'ScenarioStepRow' })

const props = defineProps({
  row: { type: Object, required: true },
  index: { type: Number, default: 0 },
  cases: { type: Array, default: () => [] },
  scenarios: { type: Array, default: () => [] },
  currentScenarioId: { type: Number, default: null },
  selection: { type: Object, required: true },
})

defineEmits(['remove'])

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
    })[props.row.type] || props.row.type,
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
    })[props.row.type] || 'info',
)

const displayName = computed(() => {
  const row = props.row
  if (row.type === 'if') {
    const c = row.config?.condition || {}
    return `如果 ${c.left || '?'} ${c.operator || 'eq'} ${c.operator === 'exists' ? '' : (c.right ?? '')}`.trim()
  }
  if (row.type === 'loop') {
    const c = row.config || {}
    if (c.mode === 'list') return `遍历 ${c.list_var || '?'}`
    if (c.mode === 'while')
      return `当 ${c.condition?.left || '?'} ${c.condition?.operator || ''} … 时循环`
    return `循环 ${c.count ?? '?'} 次`
  }
  if (row.type === 'break') return '跳出循环'
  if (row.type === 'continue') return '跳过本轮'
  if (row.type === 'http') {
    const c = row.config || {}
    return `[${c.method || 'GET'}] ${c.path || row.name || 'HTTP'}`.trim()
  }
  if (row.name) return row.name
  if (row.type === 'case') {
    const prefix = row.endpoint_method ? `[${row.endpoint_method}] ` : ''
    return `${prefix}${row.case_name || `用例#${row.ref_case_id}`}`
  }
  if (row.type === 'wait') return `等待 ${row.wait_ms} ms`
  if (row.type === 'group') return `分组（${row.children?.length || 0}）`
  return row.scenario_name || `场景#${row.ref_scenario_id}`
})
</script>

<style scoped>
.step-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  padding: 5px 6px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  line-height: 1.35;
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
  font-size: 13px;
  cursor: grab;
  color: var(--ax-text-placeholder);
}

.drag-handle:active {
  cursor: grabbing;
}

.idx {
  flex-shrink: 0;
  width: 18px;
  font-size: 11px;
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
  padding: 0 6px;
  font-size: 11px;
  line-height: 18px;
}

.step-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 400;
  color: var(--ax-text);
}

.step-row :deep(.el-button.is-link) {
  flex-shrink: 0;
  padding: 0 4px;
  font-size: 11px;
  height: auto;
}

.group-body {
  margin-left: 20px;
  border-left: 2px solid var(--ax-border);
  padding-left: 8px;
}

.group-drop {
  min-height: 8px;
}

.group-empty {
  color: var(--ax-text-placeholder);
  font-size: 11px;
  line-height: 1.35;
  padding: 4px 6px;
}

.branch-label {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--ax-text-secondary);
  margin: 4px 0 2px;
}
</style>

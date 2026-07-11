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
  () => ({ case: '用例', wait: '等待', scenario: '子场景', group: '分组' }[props.row.type] || props.row.type)
)
const typeTag = computed(
  () => ({ case: 'success', wait: 'warning', scenario: 'info', group: 'primary' }[props.row.type] || 'info')
)

const displayName = computed(() => {
  const row = props.row
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
  gap: 8px;
  margin-bottom: 6px;
  padding: 4px 6px;
  border-radius: 4px;
  cursor: pointer;
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
  cursor: grab;
  color: var(--ax-text-placeholder);
}

.drag-handle:active {
  cursor: grabbing;
}

.idx {
  width: 20px;
  color: var(--ax-text-placeholder);
  font-size: 12px;
  text-align: right;
}

.step-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-body {
  margin-left: 22px;
  border-left: 2px solid var(--ax-border);
  padding-left: 8px;
}

.group-drop {
  min-height: 8px;
}

.group-empty {
  color: var(--ax-text-placeholder);
  font-size: 12px;
  padding: 4px 6px;
}
</style>

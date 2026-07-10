<template>
  <div class="steps-editor">
    <div class="steps-col">
      <div ref="listEl">
        <div
          v-for="(row, i) in rows"
          :key="row._uid"
          class="step-row"
          :class="{ active: selectedUid === row._uid }"
          @click="selectedUid = row._uid"
        >
          <el-icon class="drag-handle" title="拖拽排序"><Rank /></el-icon>
          <span class="idx">{{ i + 1 }}</span>
          <el-checkbox v-model="row.enabled" @click.stop />
          <el-tag size="small" :type="typeTag(row.type)">{{ typeLabel(row.type) }}</el-tag>
          <span class="step-name">{{ displayName(row) }}</span>
          <el-button link type="danger" size="small" @click.stop="removeStep(i, row)">移除</el-button>
        </div>
      </div>
      <el-empty v-if="rows.length === 0" description="暂无步骤，下方添加" :image-size="50" />

      <div class="add-row">
        <el-select v-model="newType" size="small" style="width: 90px">
          <el-option label="用例" value="case" />
          <el-option label="等待" value="wait" />
          <el-option label="子场景" value="scenario" />
        </el-select>
        <el-select v-if="newType === 'case'" v-model="pickedCaseId" size="small" placeholder="选择接口用例" style="flex: 1" filterable>
          <el-option
            v-for="c in cases"
            :key="c.id"
            :label="`[${c.endpoint_method}] ${c.endpoint_name} / ${c.name}`"
            :value="c.id"
          />
        </el-select>
        <el-input-number v-else-if="newType === 'wait'" v-model="waitMs" size="small" :min="1" :step="100" style="width: 130px" />
        <el-select v-else v-model="pickedScenarioId" size="small" placeholder="选择子场景" style="flex: 1" filterable>
          <el-option v-for="s in availableScenarios" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-button size="small" type="primary" :disabled="!canAdd" @click="addStep">+ 添加</el-button>
      </div>
    </div>

    <div class="detail-col">
      <ScenarioStepDetail
        v-if="selectedStep"
        :step="selectedStep"
        :cases="cases"
        :scenarios="scenarios"
        :current-scenario-id="currentScenarioId"
        :scripts="scripts"
      />
      <el-empty v-else description="点击左侧步骤编辑详情" :image-size="60" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useDraggable } from 'vue-draggable-plus'
import ScenarioStepDetail from '@/components/apifox/ScenarioStepDetail.vue'

const props = defineProps({
  rows: { type: Array, required: true },
  cases: { type: Array, default: () => [] },
  scenarios: { type: Array, default: () => [] },
  currentScenarioId: { type: Number, default: null },
  scripts: { type: Array, default: () => [] },
})

let _seq = 0
function ensureUids() {
  props.rows.forEach((r) => {
    if (r._uid == null) r._uid = ++_seq
  })
}
onMounted(ensureUids)
watch(() => props.rows.length, ensureUids)

const listEl = ref()
useDraggable(listEl, props.rows, { animation: 150, handle: '.drag-handle' })

const selectedUid = ref(null)
const selectedStep = computed(() => props.rows.find((r) => r._uid === selectedUid.value) || null)

function removeStep(i, row) {
  if (selectedUid.value === row._uid) selectedUid.value = null
  props.rows.splice(i, 1)
}

const newType = ref('case')
const pickedCaseId = ref(null)
const pickedScenarioId = ref(null)
const waitMs = ref(500)

const availableScenarios = computed(() =>
  props.scenarios.filter((s) => s.id !== props.currentScenarioId)
)

const canAdd = computed(() => {
  if (newType.value === 'case') return !!pickedCaseId.value
  if (newType.value === 'wait') return waitMs.value > 0
  return !!pickedScenarioId.value
})

const typeLabel = (t) => ({ case: '用例', wait: '等待', scenario: '子场景' }[t] || t)
const typeTag = (t) => ({ case: 'success', wait: 'warning', scenario: 'info' }[t] || 'info')

function displayName(row) {
  if (row.type === 'case') {
    const prefix = row.endpoint_method ? `[${row.endpoint_method}] ` : ''
    return `${prefix}${row.case_name || `用例#${row.ref_case_id}`}`
  }
  if (row.type === 'wait') return `等待 ${row.wait_ms} ms`
  return row.scenario_name || `场景#${row.ref_scenario_id}`
}

function addStep() {
  if (newType.value === 'case') {
    const c = props.cases.find((x) => x.id === pickedCaseId.value)
    props.rows.push({
      type: 'case', ref_case_id: c.id, enabled: true,
      case_name: c.name, endpoint_method: c.endpoint_method, _uid: ++_seq,
    })
    pickedCaseId.value = null
  } else if (newType.value === 'wait') {
    props.rows.push({ type: 'wait', wait_ms: waitMs.value, enabled: true, _uid: ++_seq })
  } else {
    const s = props.scenarios.find((x) => x.id === pickedScenarioId.value)
    props.rows.push({
      type: 'scenario', ref_scenario_id: s.id, enabled: true, scenario_name: s.name, _uid: ++_seq,
    })
    pickedScenarioId.value = null
  }
}
</script>

<style scoped>
.steps-editor {
  display: flex;
  gap: 16px;
  height: calc(100vh - 340px);
}

.steps-col {
  width: 400px;
  flex-shrink: 0;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: 10px;
}

.detail-col {
  flex: 1;
  overflow: auto;
}

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

.add-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}
</style>

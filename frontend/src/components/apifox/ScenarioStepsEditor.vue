<template>
  <div>
    <div v-for="(row, i) in rows" :key="i" class="step-row">
      <span class="idx">{{ i + 1 }}</span>
      <el-checkbox v-model="row.enabled" />
      <el-tag size="small" :type="typeTag(row.type)">{{ typeLabel(row.type) }}</el-tag>
      <span class="step-name">{{ displayName(row) }}</span>
      <el-button link size="small" :disabled="i === 0" @click="move(i, -1)">↑</el-button>
      <el-button link size="small" :disabled="i === rows.length - 1" @click="move(i, 1)">↓</el-button>
      <el-button link type="danger" size="small" @click="rows.splice(i, 1)">移除</el-button>
    </div>
    <el-empty v-if="rows.length === 0" description="暂无步骤" :image-size="50" />

    <div class="add-row">
      <el-select v-model="newType" size="small" style="width: 100px">
        <el-option label="用例" value="case" />
        <el-option label="等待" value="wait" />
        <el-option label="子场景" value="scenario" />
      </el-select>

      <el-select
        v-if="newType === 'case'"
        v-model="pickedCaseId"
        size="small"
        placeholder="选择接口用例"
        style="width: 260px"
        filterable
      >
        <el-option
          v-for="c in cases"
          :key="c.id"
          :label="`[${c.endpoint_method}] ${c.endpoint_name} / ${c.name}`"
          :value="c.id"
        />
      </el-select>
      <el-input-number
        v-else-if="newType === 'wait'"
        v-model="waitMs"
        size="small"
        :min="1"
        :step="100"
        style="width: 140px"
      />
      <el-select
        v-else
        v-model="pickedScenarioId"
        size="small"
        placeholder="选择子场景"
        style="width: 220px"
        filterable
      >
        <el-option
          v-for="s in availableScenarios"
          :key="s.id"
          :label="s.name"
          :value="s.id"
        />
      </el-select>

      <el-button size="small" type="primary" :disabled="!canAdd" @click="addStep">+ 添加步骤</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  rows: { type: Array, required: true },
  cases: { type: Array, default: () => [] },
  scenarios: { type: Array, default: () => [] },
  currentScenarioId: { type: Number, default: null },
})

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
      case_name: c.name, endpoint_method: c.endpoint_method,
    })
    pickedCaseId.value = null
  } else if (newType.value === 'wait') {
    props.rows.push({ type: 'wait', wait_ms: waitMs.value, enabled: true })
  } else {
    const s = props.scenarios.find((x) => x.id === pickedScenarioId.value)
    props.rows.push({
      type: 'scenario', ref_scenario_id: s.id, enabled: true, scenario_name: s.name,
    })
    pickedScenarioId.value = null
  }
}

function move(i, delta) {
  const j = i + delta
  const [row] = props.rows.splice(i, 1)
  props.rows.splice(j, 0, row)
}
</script>

<style scoped>
.step-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
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

<template>
  <div class="steps-editor">
    <div class="steps-col">
      <VueDraggable
        v-model="props.rows"
        :group="{ name: 'scenario-steps' }"
        handle=".drag-handle"
        :animation="150"
      >
        <ScenarioStepRow
          v-for="(row, i) in rows"
          :key="row._uid"
          :row="row"
          :index="i"
          :cases="cases"
          :scenarios="scenarios"
          :current-scenario-id="currentScenarioId"
          :selection="selection"
          @remove="removeTop(i)"
        />
      </VueDraggable>
      <el-empty v-if="rows.length === 0" description="暂无步骤，下方添加" :image-size="50" />

      <div class="add-row">
        <el-select v-model="newType" size="small" style="width: 90px">
          <el-option label="用例" value="case" />
          <el-option label="等待" value="wait" />
          <el-option label="子场景" value="scenario" />
          <el-option label="分组" value="group" />
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
        <el-select v-else-if="newType === 'scenario'" v-model="pickedScenarioId" size="small" placeholder="选择子场景" style="flex: 1" filterable>
          <el-option v-for="s in availableScenarios" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
        <el-input v-else v-model="groupName" size="small" placeholder="分组名称" style="flex: 1" />
        <el-button size="small" type="primary" :disabled="!canAdd" @click="addStep">+ 添加</el-button>
      </div>
    </div>

    <div class="detail-col">
      <ScenarioStepDetail
        v-if="selectedStep"
        :key="selectedStep._uid"
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import ScenarioStepRow from '@/components/apifox/ScenarioStepRow.vue'
import ScenarioStepDetail from '@/components/apifox/ScenarioStepDetail.vue'

const props = defineProps({
  rows: { type: Array, required: true },
  cases: { type: Array, default: () => [] },
  scenarios: { type: Array, default: () => [] },
  currentScenarioId: { type: Number, default: null },
  scripts: { type: Array, default: () => [] },
})

let _seq = 0
function ensureUids(rows) {
  rows.forEach((r) => {
    if (r._uid == null) r._uid = ++_seq
    if (r.type === 'group') {
      if (!Array.isArray(r.children)) r.children = []
      ensureUids(r.children)
    }
  })
}
onMounted(() => ensureUids(props.rows))
watch(() => props.rows.length, () => ensureUids(props.rows))

// 选中态用共享 reactive（UI 态，非业务数据，显式传 prop，不走 provide/inject）
const selection = reactive({ uid: null })

function findByUid(rows, uid) {
  for (const r of rows) {
    if (r._uid === uid) return r
    if (r.type === 'group' && r.children) {
      const hit = findByUid(r.children, uid)
      if (hit) return hit
    }
  }
  return null
}
const selectedStep = computed(() => findByUid(props.rows, selection.uid))

function removeTop(i) {
  if (props.rows[i]?._uid === selection.uid) selection.uid = null
  props.rows.splice(i, 1)
}

const newType = ref('case')
const pickedCaseId = ref(null)
const pickedScenarioId = ref(null)
const waitMs = ref(500)
const groupName = ref('')

const availableScenarios = computed(() =>
  props.scenarios.filter((s) => s.id !== props.currentScenarioId)
)

const canAdd = computed(() => {
  if (newType.value === 'case') return !!pickedCaseId.value
  if (newType.value === 'wait') return waitMs.value > 0
  if (newType.value === 'scenario') return !!pickedScenarioId.value
  return true
})

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
  } else if (newType.value === 'scenario') {
    const s = props.scenarios.find((x) => x.id === pickedScenarioId.value)
    props.rows.push({
      type: 'scenario', ref_scenario_id: s.id, enabled: true, scenario_name: s.name, _uid: ++_seq,
    })
    pickedScenarioId.value = null
  } else {
    props.rows.push({
      type: 'group', name: groupName.value || '分组', enabled: true, children: [], _uid: ++_seq,
    })
    groupName.value = ''
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

.add-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}
</style>

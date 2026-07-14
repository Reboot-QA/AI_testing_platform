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
          <el-option label="条件" value="if" />
          <el-option label="循环" value="loop" />
          <el-option label="跳出循环" value="break" />
          <el-option label="跳过本轮" value="continue" />
          <el-option label="数据库操作" value="db" />
          <el-option label="HTTP 请求" value="http" />
          <el-option label="从接口导入" value="import-endpoint" />
          <el-option label="从 cURL 导入" value="import-curl" />
        </el-select>

        <el-select
          v-if="newType === 'import-endpoint'"
          v-model="pickedEndpointId"
          size="small"
          placeholder="选择接口"
          style="flex: 1"
          filterable
        >
          <el-option
            v-for="ep in endpoints"
            :key="ep.id"
            :label="`[${ep.method}] ${ep.name}`"
            :value="ep.id"
          />
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
        <el-input v-else-if="newType === 'group'" v-model="groupName" size="small" placeholder="分组名称" style="flex: 1" />
        <span v-else-if="newType === 'break' || newType === 'continue'" class="add-hint">添加后拖入循环体内</span>
        <span v-else class="add-hint">添加后在右侧配置</span>
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
        :databases="databases"
        :server-names="serverNames"
      />
      <el-empty v-else description="点击左侧步骤编辑详情" :image-size="60" />
    </div>

    <el-dialog v-model="curlVisible" title="从 cURL 导入" width="560px">
      <el-input
        v-model="curlText"
        type="textarea"
        :rows="8"
        placeholder="粘贴 curl 命令，如 curl 'https://...' -X POST -H '...' --data-raw '...'"
      />
      <template #footer>
        <el-button @click="curlVisible = false">取消</el-button>
        <el-button type="primary" @click="importFromCurl">解析并添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { VueDraggable } from 'vue-draggable-plus'
import { apifoxApi } from '@/api'
import { emptySpec, normalizeSpec } from '@/utils/apifoxSpec'
import { parseCurl } from '@/utils/curlParser'
import ScenarioStepRow from '@/components/apifox/ScenarioStepRow.vue'
import ScenarioStepDetail from '@/components/apifox/ScenarioStepDetail.vue'

const props = defineProps({
  rows: { type: Array, required: true },
  cases: { type: Array, default: () => [] },
  scenarios: { type: Array, default: () => [] },
  currentScenarioId: { type: Number, default: null },
  scripts: { type: Array, default: () => [] },
  databases: { type: Array, default: () => [] },
  endpoints: { type: Array, default: () => [] },
  serverNames: { type: Array, default: () => [] },
})

let _seq = 0
// 容器步骤的可嵌套子列表：分组一个，条件(if)两个（then=children / else=elseChildren）
function stepChildLists(r) {
  if (r.type === 'group' || r.type === 'loop') {
    if (!Array.isArray(r.children)) r.children = []
    return [r.children]
  }
  if (r.type === 'if') {
    if (!Array.isArray(r.children)) r.children = []
    if (!Array.isArray(r.elseChildren)) r.elseChildren = []
    return [r.children, r.elseChildren]
  }
  return []
}

function ensureUids(rows) {
  rows.forEach((r) => {
    if (r._uid == null) r._uid = ++_seq
    stepChildLists(r).forEach(ensureUids)
  })
}
onMounted(() => ensureUids(props.rows))
watch(() => props.rows.length, () => ensureUids(props.rows))

// 选中态用共享 reactive（UI 态，非业务数据，显式传 prop，不走 provide/inject）
const selection = reactive({ uid: null })

function findByUid(rows, uid) {
  for (const r of rows) {
    if (r._uid === uid) return r
    for (const list of stepChildLists(r)) {
      const hit = findByUid(list, uid)
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
const pickedEndpointId = ref(null)
const waitMs = ref(500)
const groupName = ref('')
const curlVisible = ref(false)
const curlText = ref('')

const availableScenarios = computed(() =>
  props.scenarios.filter((s) => s.id !== props.currentScenarioId)
)

const canAdd = computed(() => {
  if (newType.value === 'case') return !!pickedCaseId.value
  if (newType.value === 'wait') return waitMs.value > 0
  if (newType.value === 'scenario') return !!pickedScenarioId.value
  if (newType.value === 'import-endpoint') return !!pickedEndpointId.value
  return true
})

function newHttpStep(over = {}) {
  return {
    type: 'http', enabled: true, name: over.name || 'HTTP 请求', _uid: ++_seq,
    config: {
      name: over.name || '', method: over.method || 'GET', path: over.path || '',
      server_name: over.server_name || null,
      // 统一归一化请求结构，两个导入路径与空步骤保持一致的形状
      request_spec: normalizeSpec(over.request_spec || emptySpec()),
      assertions: over.assertions || [], extracts: over.extracts || [],
    },
  }
}

async function importFromEndpoint() {
  try {
    const e = await apifoxApi.getEndpoint(pickedEndpointId.value)
    props.rows.push(newHttpStep({
      name: e.name, method: e.method, path: e.path, server_name: e.server_name,
      request_spec: e.request_spec,
      assertions: e.assertions || [], extracts: e.extracts || [],
    }))
    pickedEndpointId.value = null
    newType.value = 'http'
  } catch {
    ElMessage.error('接口加载失败')
  }
}

function importFromCurl() {
  const parsed = parseCurl(curlText.value)
  if (!parsed) {
    ElMessage.error('无法解析，请粘贴以 curl 开头的完整命令')
    return
  }
  props.rows.push(newHttpStep(parsed))
  curlVisible.value = false
  curlText.value = ''
  newType.value = 'http'
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
  } else if (newType.value === 'scenario') {
    const s = props.scenarios.find((x) => x.id === pickedScenarioId.value)
    props.rows.push({
      type: 'scenario', ref_scenario_id: s.id, enabled: true, scenario_name: s.name, _uid: ++_seq,
    })
    pickedScenarioId.value = null
  } else if (newType.value === 'group') {
    props.rows.push({
      type: 'group', name: groupName.value || '分组', enabled: true, children: [], _uid: ++_seq,
    })
    groupName.value = ''
  } else if (newType.value === 'if') {
    props.rows.push({
      type: 'if', enabled: true, _uid: ++_seq,
      config: { condition: { left: '', operator: 'eq', right: '' } },
      children: [], elseEnabled: false, elseChildren: [],
    })
  } else if (newType.value === 'break' || newType.value === 'continue') {
    props.rows.push({ type: newType.value, enabled: true, _uid: ++_seq })
  } else if (newType.value === 'db') {
    props.rows.push({
      type: 'db', enabled: true, name: '数据库操作', _uid: ++_seq,
      config: { connection_id: null, sql: '', extracts: [] },
    })
  } else if (newType.value === 'http') {
    props.rows.push(newHttpStep())
  } else if (newType.value === 'import-endpoint') {
    importFromEndpoint()
  } else if (newType.value === 'import-curl') {
    curlVisible.value = true
  } else {
    props.rows.push({
      type: 'loop', enabled: true, _uid: ++_seq, children: [],
      config: {
        mode: 'count', count: 1, list_var: '', item_var: 'item', index_var: 'index',
        max_iterations: 10, condition: { left: '', operator: 'eq', right: '' },
      },
    })
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

.add-hint {
  flex: 1;
  font-size: 12px;
  color: var(--ax-text-placeholder);
}
</style>

<template>
  <div class="cases-panel">
    <div class="list">
      <div class="list-head">
        <span>用例</span>
        <el-button size="small" type="primary" @click="addCase"><el-icon><Plus /></el-icon></el-button>
      </div>
      <div
        v-for="c in cases"
        :key="c.id"
        class="case-item"
        :class="{ active: form.id === c.id }"
        @click="selectCase(c.id)"
      >
        <span class="name">{{ c.name }}</span>
        <el-button link type="danger" size="small" @click.stop="delCase(c)">删</el-button>
      </div>
      <el-empty v-if="!cases.length" description="暂无用例" :image-size="50" />
    </div>

    <div class="editor">
      <template v-if="form.id">
        <div class="run-bar">
          <el-select v-model="runEnvId" placeholder="选择环境" size="small" style="width: 180px" clearable>
            <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>
          <el-button size="small" type="success" :loading="running" @click="runCase">运行</el-button>
        </div>
        <CaseEditor :form="form" :saving="saving" :scripts="scripts" @save="saveCase" />
        <RunProgress :events="runEvents" :running="running" @clear="runEvents = []" />
      </template>
      <el-empty v-else description="选择或新建一个用例" :image-size="60" />
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { ensureKvRows } from '@/utils/apiCaseConfig'
import { emptySpec, normalizeSpec as normSpec } from '@/utils/apifoxSpec'
import CaseEditor from '@/components/apifox/CaseEditor.vue'
import RunProgress from '@/components/apifox/RunProgress.vue'

const props = defineProps({
  endpointId: { type: [String, Number], required: true },
  projectId: { type: [String, Number], required: true },
  environments: { type: Array, default: () => [] },
})

const cases = ref([])
const scripts = ref([])
const saving = ref(false)
const running = ref(false)
const runEnvId = ref(null)
const runEvents = ref([])

const form = reactive({
  id: null, name: '', request_spec: emptySpec(), variables: [], assertions: [], extracts: [],
  pre_scripts: [], post_scripts: [], data_drive: { enabled: false, rows: [] },
})

async function loadCases() {
  cases.value = props.endpointId ? await apifoxApi.listCases(props.endpointId) : []
}

async function loadScripts() {
  scripts.value = await apifoxApi.listScripts(props.projectId)
}

function emptyCasePayload(name) {
  return {
    name, request_spec: emptySpec(), variables: [],
    data_drive: { enabled: false, rows: [] }, assertions: [], extracts: [],
    pre_scripts: [], post_scripts: [],
  }
}

function applyCase(c) {
  form.id = c.id
  form.name = c.name
  form.request_spec = normSpec(c.request_spec)
  form.variables = ensureKvRows(c.variables || [])
  form.assertions = c.assertions || []
  form.extracts = c.extracts || []
  form.pre_scripts = c.pre_scripts || []
  form.post_scripts = c.post_scripts || []
  form.data_drive = c.data_drive?.enabled !== undefined ? c.data_drive : { enabled: false, rows: [] }
}

async function addCase() {
  const { value } = await ElMessageBox.prompt('用例名称', '新建用例', { inputPattern: /\S/, inputErrorMessage: '不能为空' })
  const created = await apifoxApi.createCase(props.endpointId, emptyCasePayload(value))
  ElMessage.success('已创建')
  await loadCases()
  applyCase(created)
}

async function selectCase(cid) {
  applyCase(await apifoxApi.getCase(cid))
}

async function delCase(c) {
  await ElMessageBox.confirm(`确认删除用例「${c.name}」？`, '提示', { type: 'warning' })
  await apifoxApi.deleteCase(c.id)
  if (form.id === c.id) form.id = null
  ElMessage.success('已删除')
  await loadCases()
}

async function saveCase() {
  saving.value = true
  try {
    await apifoxApi.updateCase(form.id, {
      name: form.name, request_spec: form.request_spec, variables: form.variables,
      data_drive: form.data_drive, assertions: form.assertions, extracts: form.extracts,
      pre_scripts: form.pre_scripts.map(({ script_id, enabled }) => ({ script_id, enabled })),
      post_scripts: form.post_scripts.map(({ script_id, enabled }) => ({ script_id, enabled })),
    })
    ElMessage.success('已保存')
    await loadCases()
  } finally {
    saving.value = false
  }
}

async function runCase() {
  runEvents.value = []
  running.value = true
  try {
    await apifoxApi.runCaseStream(form.id, runEnvId.value, (e) => runEvents.value.push(e))
  } catch (e) {
    ElMessage.error(e.message || '运行失败')
  } finally {
    running.value = false
  }
}

watch(
  () => props.environments,
  (list) => {
    if (!runEnvId.value) {
      const def = list.find((e) => e.is_default)
      if (def) runEnvId.value = def.id
    }
  },
  { immediate: true }
)

watch(
  () => props.endpointId,
  () => { form.id = null; loadCases() },
  { immediate: true }
)

loadScripts()
</script>

<style scoped>
.cases-panel {
  display: flex;
  gap: 12px;
  height: calc(100vh - 320px);
}

.list {
  width: 200px;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: 6px;
}

.list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 8px;
}

.case-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.case-item:hover {
  background: var(--ax-bg-hover);
}

.case-item.active {
  background: var(--ax-bg-active);
}

.name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor {
  flex: 1;
  overflow: auto;
}

.run-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}
</style>

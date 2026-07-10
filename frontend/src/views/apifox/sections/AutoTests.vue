<template>
  <div>
    <el-radio-group v-model="section" size="small" class="section-switch">
      <el-radio-button value="cases">单接口用例</el-radio-button>
      <el-radio-button value="scenarios">场景用例</el-radio-button>
      <el-radio-button value="schedules">定时任务</el-radio-button>
    </el-radio-group>

    <ScenarioPanel v-if="section === 'scenarios'" class="auto-tests" />
    <SchedulePanel v-else-if="section === 'schedules'" />
    <div v-else class="auto-tests">
    <div class="list-panel">
      <div class="field">
        <span class="lbl">接口</span>
        <el-select
          v-model="selectedEndpointId"
          placeholder="选择接口"
          size="small"
          filterable
          style="width: 100%"
          @change="onEndpointChange"
        >
          <el-option v-for="e in endpoints" :key="e.id" :label="`${e.method} ${e.name}`" :value="e.id">
            <MethodTag :method="e.method" /> <span class="opt-name">{{ e.name }}</span>
          </el-option>
        </el-select>
      </div>

      <div v-if="selectedEndpointId" class="cases">
        <div class="cases-head">
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
          <span class="case-name">{{ c.name }}</span>
          <el-button link type="danger" size="small" @click.stop="delCase(c)">删</el-button>
        </div>
        <el-empty v-if="cases.length === 0" description="暂无用例" :image-size="60" />
      </div>
    </div>

    <div class="editor-panel">
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
      <el-empty v-else description="选择接口后新建/选择用例" />
    </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { ensureKvRows } from '@/utils/apiCaseConfig'
import { emptySpec, normalizeSpec as normSpec } from '@/utils/apifoxSpec'
import CaseEditor from '@/components/apifox/CaseEditor.vue'
import RunProgress from '@/components/apifox/RunProgress.vue'
import ScenarioPanel from '@/views/apifox/sections/ScenarioPanel.vue'
import SchedulePanel from '@/views/apifox/sections/SchedulePanel.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const section = ref('cases')
const endpoints = ref([])
const selectedEndpointId = ref(null)
const cases = ref([])
const scripts = ref([])
const environments = ref([])
const saving = ref(false)
const running = ref(false)
const runEnvId = ref(null)
const runEvents = ref([])

const form = reactive({
  id: null, name: '', request_spec: emptySpec(), variables: [], assertions: [], extracts: [],
  pre_scripts: [], post_scripts: [],
  data_drive: { enabled: false, rows: [] },
})

async function loadEndpoints() {
  endpoints.value = await apifoxApi.listEndpoints(pid.value)
}

async function loadScripts() {
  scripts.value = await apifoxApi.listScripts(pid.value)
}

async function loadEnvironments() {
  environments.value = await apifoxApi.listEnvironments(pid.value)
  const def = environments.value.find((e) => e.is_default)
  if (def && !runEnvId.value) runEnvId.value = def.id
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

async function loadCases() {
  cases.value = selectedEndpointId.value ? await apifoxApi.listCases(selectedEndpointId.value) : []
}

function onEndpointChange() {
  form.id = null
  loadCases()
}

function emptyCasePayload(name) {
  return {
    name, request_spec: emptySpec(), variables: [],
    data_drive: { enabled: false, rows: [] }, assertions: [], extracts: [],
    pre_scripts: [], post_scripts: [],
  }
}

async function addCase() {
  const { value } = await ElMessageBox.prompt('用例名称', '新建用例', { inputPattern: /\S/, inputErrorMessage: '不能为空' })
  const created = await apifoxApi.createCase(selectedEndpointId.value, emptyCasePayload(value))
  ElMessage.success('已创建')
  await loadCases()
  applyCase(created)
}

async function selectCase(cid) {
  applyCase(await apifoxApi.getCase(cid))
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

onMounted(async () => {
  await loadEndpoints()
  await loadScripts()
  await loadEnvironments()
})
</script>

<style scoped>
.section-switch {
  margin-bottom: 12px;
}

.opt-name {
  margin-left: 6px;
}

.run-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.auto-tests {
  display: flex;
  gap: 16px;
  height: calc(100vh - 260px);
}

.list-panel {
  width: 260px;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: 8px;
}

.field {
  margin-bottom: 12px;
}

.lbl {
  font-size: 13px;
  color: var(--ax-text-secondary);
  display: block;
  margin-bottom: 4px;
}

.cases-head {
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

.case-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-panel {
  flex: 1;
  overflow: auto;
}
</style>

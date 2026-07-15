<template>
  <div class="cases-panel">
    <div class="list">
      <div class="list-head">
        <span>用例</span>
        <div class="head-actions">
          <el-button size="small" @click="aiGenerate">
            <el-icon><MagicStick /></el-icon> AI 生成
          </el-button>
          <el-button size="small" type="primary" @click="addCase"><el-icon><Plus /></el-icon></el-button>
        </div>
      </div>

      <el-radio-group v-model="filter" size="small" class="cat-filter">
        <el-radio-button v-for="f in CATEGORY_FILTERS" :key="f.value" :value="f.value">{{ f.label }}</el-radio-button>
      </el-radio-group>

      <div
        v-for="c in filteredCases"
        :key="c.id"
        class="case-item"
        :class="{ active: form.id === c.id }"
        @click="selectCase(c.id)"
      >
        <el-tag size="small" :type="tagType(c.category)">{{ categoryLabel(c.category) }}</el-tag>
        <span class="name">{{ c.name }}</span>
        <el-button link size="small" @click.stop="copyCase(c)">复制</el-button>
        <el-button link type="danger" size="small" @click.stop="delCase(c)">删</el-button>
      </div>
      <el-empty v-if="!filteredCases.length" description="暂无用例" :image-size="50" />
    </div>

    <div class="editor">
      <template v-if="form.id">
        <div class="run-bar">
          <el-button size="small" type="success" :loading="running" @click="runCase">运行</el-button>
          <span class="cat-label">分类</span>
          <el-select v-model="form.category" size="small" style="width: 110px">
            <el-option v-for="c in CASE_CATEGORIES" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
          <span class="run-hint">环境在顶部选择</span>
        </div>
        <CaseEditor :form="form" :saving="saving" :scripts="scripts" :datasets="datasets" @save="saveCase" />
        <RunProgress :events="runEvents" :running="running" @clear="runEvents = []" />
      </template>
      <el-empty v-else description="选择或新建一个用例" :image-size="60" />
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { ensureKvRows } from '@/utils/apiCaseConfig'
import { emptySpec, normalizeSpec as normSpec } from '@/utils/apifoxSpec'
import { CASE_CATEGORIES, CATEGORY_FILTERS, categoryLabel } from '@/utils/caseCategory'
import { isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import CaseEditor from '@/components/apifox/CaseEditor.vue'
import RunProgress from '@/components/apifox/RunProgress.vue'

const props = defineProps({
  endpointId: { type: [String, Number], required: true },
  projectId: { type: [String, Number], required: true },
})

const store = useWorkspaceStore()
const cases = ref([])
const scripts = ref([])
const datasets = ref([])
const saving = ref(false)
const running = ref(false)
const runEvents = ref([])
const filter = ref('all')

const filteredCases = computed(() =>
  filter.value === 'all' ? cases.value : cases.value.filter((c) => c.category === filter.value)
)

const tagType = (cat) => ({ positive: 'success', negative: 'warning', boundary: '', security: 'danger' }[cat] || 'info')

const form = reactive({
  id: null, name: '', category: 'other', request_spec: emptySpec(), variables: [], assertions: [], extracts: [],
  pre_scripts: [], post_scripts: [], data_drive: { enabled: false, rows: [] }, version: 1,
})

async function loadCases() {
  cases.value = props.endpointId ? await apifoxApi.listCases(props.endpointId) : []
}

function emptyCasePayload(name, category) {
  return {
    name, category, request_spec: emptySpec(), variables: [],
    data_drive: { enabled: false, rows: [] }, assertions: [], extracts: [],
    pre_scripts: [], post_scripts: [],
  }
}

function applyCase(c) {
  form.id = c.id
  form.name = c.name
  form.category = c.category || 'other'
  form.request_spec = normSpec(c.request_spec)
  form.variables = ensureKvRows(c.variables || [])
  form.assertions = c.assertions || []
  form.extracts = c.extracts || []
  form.pre_scripts = c.pre_scripts || []
  form.post_scripts = c.post_scripts || []
  form.data_drive = c.data_drive?.enabled !== undefined ? c.data_drive : { enabled: false, rows: [] }
  form.version = c.version ?? 1
}

async function addCase() {
  const { value } = await ElMessageBox.prompt('用例名称', '新建用例', { inputPattern: /\S/, inputErrorMessage: '不能为空' })
  // 当前过滤了某分类时，新建默认归入该分类；「全部」时归「其他」
  const category = filter.value === 'all' ? 'other' : filter.value
  const payload = emptyCasePayload(value, category)
  // 带入接口默认参数：新用例继承接口已配置的 params/headers/body/auth，不从空白开始
  try {
    const ep = await apifoxApi.getEndpoint(props.endpointId)
    if (ep?.request_spec) payload.request_spec = ep.request_spec
  } catch { /* 拉取接口失败则用空 spec，不阻塞建用例 */ }
  const created = await apifoxApi.createCase(props.endpointId, payload)
  ElMessage.success('已创建')
  await loadCases()
  applyCase(created)
}

function aiGenerate() {
  // 前端按钮占位：AI 生成用例后端待接入（正向/逆向/边界值/安全性），见进度计划
  ElMessage.info('AI 生成用例功能开发中，后端待接入')
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

async function copyCase(c) {
  const created = await apifoxApi.copyCase(c.id)
  ElMessage.success('已复制')
  await loadCases()
  applyCase(created)
}

function casePayload() {
  return {
    name: form.name, category: form.category, request_spec: form.request_spec, variables: form.variables,
    data_drive: form.data_drive, assertions: form.assertions, extracts: form.extracts,
    pre_scripts: form.pre_scripts.map(({ script_id, enabled }) => ({ script_id, enabled })),
    post_scripts: form.post_scripts.map(({ script_id, enabled }) => ({ script_id, enabled })),
  }
}

async function doSaveCase() {
  const updated = await apifoxApi.updateCase(form.id, { ...casePayload(), expected_version: form.version })
  form.version = updated.version
  await loadCases()
}

async function saveCase() {
  saving.value = true
  try {
    await doSaveCase()
    ElMessage.success('已保存')
  } catch (e) {
    if (!isConflict(e)) throw e
    await resolveSaveConflict({
      reload: () => selectCase(form.id),
      overwrite: async () => {
        const latest = await apifoxApi.getCase(form.id)
        form.version = latest.version
        await doSaveCase()
      },
    })
  } finally {
    saving.value = false
  }
}

async function runCase() {
  runEvents.value = []
  running.value = true
  try {
    await apifoxApi.runCaseStream(form.id, store.currentEnvironmentId, (e) => runEvents.value.push(e))
  } catch (e) {
    ElMessage.error(e.message || '运行失败')
  } finally {
    running.value = false
  }
}

watch(
  () => props.endpointId,
  () => { form.id = null; loadCases() },
  { immediate: true }
)

apifoxApi.listScripts(props.projectId).then((r) => (scripts.value = r))
apifoxApi.listDatasets(props.projectId).then((r) => (datasets.value = r))
</script>

<style scoped>
.cases-panel {
  display: flex;
  gap: 12px;
  height: calc(100vh - 360px);
}

.list {
  width: 220px;
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

.head-actions {
  display: flex;
  gap: 6px;
}

.cat-filter {
  display: flex;
  flex-wrap: wrap;
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
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.cat-label {
  font-size: 13px;
  color: var(--ax-text-secondary);
}

.run-hint {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}
</style>

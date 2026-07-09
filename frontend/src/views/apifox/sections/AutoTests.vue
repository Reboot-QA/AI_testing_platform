<template>
  <div class="auto-tests">
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
          <el-option v-for="e in endpoints" :key="e.id" :label="`${e.method} ${e.name}`" :value="e.id" />
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
      <CaseEditor v-if="form.id" :form="form" :saving="saving" @save="saveCase" />
      <el-empty v-else description="选择接口后新建/选择用例" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { ensureKvRows } from '@/utils/apiCaseConfig'
import CaseEditor from '@/components/apifox/CaseEditor.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const endpoints = ref([])
const selectedEndpointId = ref(null)
const cases = ref([])
const saving = ref(false)

const form = reactive({
  id: null, name: '', request_spec: emptySpec(), variables: [], assertions: [], extracts: [],
  data_drive: { enabled: false, rows: [] },
})

function emptySpec() {
  return {
    query: [], path_params: [], headers: [],
    body: { type: 'none', raw: '', form: [] },
    auth: { type: 'none', token: '', username: '', password: '' },
  }
}

function normSpec(s) {
  s = s || {}
  const b = s.body || {}
  return {
    query: ensureKvRows(s.query || []),
    path_params: ensureKvRows(s.path_params || []),
    headers: ensureKvRows(s.headers || []),
    body: { type: b.type || 'none', raw: b.raw || '', form: ensureKvRows(b.form || []) },
    auth: {
      type: s.auth?.type || 'none', token: s.auth?.token || '',
      username: s.auth?.username || '', password: s.auth?.password || '',
    },
  }
}

async function loadEndpoints() {
  endpoints.value = await apifoxApi.listEndpoints(pid.value)
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
    })
    ElMessage.success('已保存')
    await loadCases()
  } finally {
    saving.value = false
  }
}

onMounted(loadEndpoints)
</script>

<style scoped>
.auto-tests {
  display: flex;
  gap: 16px;
  height: calc(100vh - 220px);
}

.list-panel {
  width: 260px;
  border-right: 1px solid #e2e8f0;
  overflow: auto;
  padding-right: 8px;
}

.field {
  margin-bottom: 12px;
}

.lbl {
  font-size: 13px;
  color: #64748b;
  display: block;
  margin-bottom: 4px;
}

.cases-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: #1a365d;
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
  background: #f1f5f9;
}

.case-item.active {
  background: #e0ecff;
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

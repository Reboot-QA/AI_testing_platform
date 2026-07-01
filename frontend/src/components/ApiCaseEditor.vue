<template>
  <div class="api-case-editor">
    <div class="editor-toolbar">
      <div class="toolbar-left">
        <el-button type="primary" :disabled="!suiteId" @click="handleNew">
          <el-icon><Plus /></el-icon> 新建
        </el-button>
        <el-button type="primary" :loading="saving" :disabled="!suiteId" @click="handleSave">
          <el-icon><DocumentChecked /></el-icon> 保存
        </el-button>
        <el-button type="success" :loading="sending" :disabled="!canSend" @click="handleSend">
          <el-icon><Promotion /></el-icon> {{ sendButtonLabel }}
        </el-button>
        <el-select
          v-if="showDataDriveSelector"
          v-model="dataDriveRunMode"
          size="small"
          style="width: 160px"
          placeholder="选择数据集"
        >
          <el-option
            v-for="(option, index) in dataDriveRunOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button :disabled="!canAiGenerateData" :loading="aiGenerating" @click="handleAiGenerateData">
          <el-icon><MagicStick /></el-icon> AI 生成数据
        </el-button>
        <el-button :disabled="!suiteId" @click="$emit('import')">
          <el-icon><Upload /></el-icon> 导入
        </el-button>
        <el-button :disabled="!editingId || !suiteId" :loading="copying" @click="handleCopy">
          <el-icon><CopyDocument /></el-icon> 复制
        </el-button>
      </div>
      <div class="toolbar-right">
        <span class="env-label">环境</span>
        <el-select
          v-model="form.environment_id"
          style="width: 260px"
          placeholder="选择环境"
          @change="syncEnvHeaders"
        >
          <el-option
            v-for="e in environments"
            :key="e.id"
            :label="`${e.name}（${e.base_url}）`"
            :value="e.id"
          />
        </el-select>
      </div>
    </div>

    <div class="editor-main">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="0">
        <div class="name-row">
          <el-form-item prop="name" class="name-form-item">
            <el-input v-model="form.name" placeholder="用例名称" />
          </el-form-item>
        </div>

        <div class="url-row">
          <el-select v-model="form.method" class="method-select">
            <el-option v-for="m in methods" :key="m" :label="m" :value="m" />
          </el-select>
          <el-input
            v-model="form.full_url"
            placeholder="https://api.example.com/path"
            class="url-input"
            @blur="syncQueryFromUrl"
            @paste="onUrlPaste"
          />
        </div>

        <el-tabs v-model="activeTab" class="request-tabs apipost-tabs">
          <el-tab-pane :label="`Header (${activeHeaderCount})`" name="headers">
            <ApiKvParamTable
              v-model:rows="headerRows"
              key-label="Header 名"
              value-label="Header 值"
              key-placeholder="Content-Type"
            />
          </el-tab-pane>

          <el-tab-pane :label="`Query (${activeQueryCount})`" name="query">
            <ApiKvParamTable v-model:rows="queryRows" key-placeholder="param" value-placeholder="value" />
          </el-tab-pane>

          <el-tab-pane :label="`Path (${activePathCount})`" name="path">
            <div class="form-tip path-tip">路径变量用于替换 URL 中的 {变量名}，如 /users/{id}</div>
            <ApiKvParamTable
              v-model:rows="pathRows"
              key-label="变量名"
              value-label="变量值"
              :show-desc="false"
              :show-bulk="false"
            />
          </el-tab-pane>

          <el-tab-pane :label="`Body (${activeBodyCount})`" name="body">
            <el-radio-group v-model="form.body_type" class="body-type-group">
              <el-radio-button label="none">none</el-radio-button>
              <el-radio-button label="form-data">form-data</el-radio-button>
              <el-radio-button label="urlencoded">urlencoded</el-radio-button>
              <el-radio-button label="json">json</el-radio-button>
              <el-radio-button label="raw">raw</el-radio-button>
            </el-radio-group>
            <ApiKvParamTable
              v-if="form.body_type === 'form-data' || form.body_type === 'urlencoded'"
              v-model:rows="currentFormBodyRows"
              :show-desc="false"
              :show-bulk="false"
              show-batch-delete
            >
              <template #toolbar-extra>
                <el-button size="small" @click="openJsonImport">从 JSON 导入</el-button>
                <el-button size="small" @click="handleExportJson">导出 JSON</el-button>
              </template>
            </ApiKvParamTable>
            <div v-else-if="form.body_type === 'json'" class="body-editor-wrap">
              <div class="body-editor-toolbar">
                <el-button size="small" :loading="aiGenerating" :disabled="!canAiGenerateData" @click="handleAiGenerateData">
                  AI 生成数据
                </el-button>
              </div>
              <el-input
                v-model="bodyStores.json"
                type="textarea"
                :rows="10"
                class="body-editor"
                placeholder='{"key":"value"}'
              />
            </div>
            <div v-else-if="form.body_type === 'raw'" class="body-editor-wrap">
              <div class="body-editor-toolbar">
                <el-button size="small" :loading="aiGenerating" :disabled="!canAiGenerateData" @click="handleAiGenerateData">
                  AI 生成数据
                </el-button>
              </div>
              <el-input
                v-model="bodyStores.raw"
                type="textarea"
                :rows="10"
                class="body-editor"
                placeholder="raw body"
              />
            </div>
          </el-tab-pane>

          <el-tab-pane label="认证" name="auth">
            <el-form label-width="90px" class="auth-form">
              <el-form-item label="认证方式">
                <el-select v-model="form.auth.type" style="width: 220px">
                  <el-option label="No Auth" value="none" />
                  <el-option label="Bearer Token" value="bearer" />
                  <el-option label="Basic Auth" value="basic" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="form.auth.type === 'bearer'" label="Token">
                <el-input v-model="form.auth.token" placeholder="Bearer Token" />
              </el-form-item>
              <template v-if="form.auth.type === 'basic'">
                <el-form-item label="用户名">
                  <el-input v-model="form.auth.username" />
                </el-form-item>
                <el-form-item label="密码">
                  <el-input v-model="form.auth.password" type="password" show-password />
                </el-form-item>
              </template>
            </el-form>
          </el-tab-pane>

          <el-tab-pane :label="`Cookie (${activeCookieCount})`" name="cookie">
            <ApiKvParamTable v-model:rows="cookieRows" key-placeholder="cookie名" value-placeholder="cookie值" />
          </el-tab-pane>

          <el-tab-pane :label="`参数化 (${activeVariableCount})`" name="variables">
            <div class="form-tip">
              在 URL、Header、Query、Body 中使用 <code v-pre>{{变量名}}</code> 引用，发送/执行时自动替换
            </div>
            <div class="section-label">变量定义</div>
            <ApiKvParamTable
              v-model:rows="variableRows"
              key-label="变量名"
              value-label="变量值"
              key-placeholder="phone"
              value-placeholder="17341587465"
              :show-bulk="false"
              show-batch-delete
            />

            <div class="data-drive-section">
              <div class="section-header">
                <span class="section-label">数据驱动</span>
                <el-switch v-model="dataDriveEnabled" active-text="启用多组数据" />
              </div>
              <div v-if="dataDriveEnabled" class="form-tip">
                每组数据会覆盖同名变量的默认值；套件执行时按启用数据集逐条运行
              </div>
              <ApiDataDriveTable
                v-if="dataDriveEnabled"
                v-model:rows="dataDriveRows"
                :variable-rows="variableRows"
              />
            </div>
          </el-tab-pane>

          <el-tab-pane name="pre">
            <template #label>
              <span class="tab-with-dot">
                预执行操作
                <i v-if="hasConfiguredPreOperations" class="tab-config-dot" />
              </span>
            </template>
            <ApiCaseOperationList
              v-model:operations="preOperations"
              phase="pre"
              :debug-result="preScriptDebugResult"
              :debugging-id="preScriptDebuggingId"
              :debug-loading="preScriptDebuggingLoading"
              :debug-variable-rows="preScriptVariableRows"
              @debug-script="handlePreScriptDebug"
            />
          </el-tab-pane>

          <el-tab-pane name="post">
            <template #label>
              <span class="tab-with-dot">
                后执行操作
                <i v-if="hasConfiguredPostOperations" class="tab-config-dot" />
              </span>
            </template>
            <ApiCaseOperationList
              v-model:operations="postOperations"
              phase="post"
              :response-body="displayedDebug?.response_body || debugResult?.response_body || ''"
              :debug-result="postScriptDebugResult"
              :debugging-id="postScriptDebuggingId"
              :debug-loading="postScriptDebuggingLoading"
              :debug-variable-rows="postScriptVariableRows"
              @debug-script="handlePostScriptDebug"
            >
              <template #footer>
                <el-row :gutter="16" class="settings-inline post-settings-row">
                  <el-col :span="12">
                    <span class="inline-label">排序</span>
                    <el-input-number v-model="form.sort_order" :min="0" size="small" />
                  </el-col>
                  <el-col :span="12" class="enable-col">
                    <span class="inline-label">启用</span>
                    <el-switch v-model="form.enabled" />
                  </el-col>
                </el-row>
              </template>
            </ApiCaseOperationList>
          </el-tab-pane>
        </el-tabs>
      </el-form>
    </div>

    <div v-if="debugResult" class="editor-response">
      <div class="response-toolbar">
        <el-tag :type="debugResult.status === 'passed' ? 'success' : 'danger'" size="small">
          {{ debugResult.status === 'passed' ? '成功' : '失败' }}
        </el-tag>
        <span v-if="debugResult.response_status" class="response-meta">
          HTTP {{ debugResult.response_status }} · {{ formatDuration(debugResult.duration_ms) }}
        </span>
        <span v-if="debugResult.iterations?.length" class="response-meta">
          共 {{ debugResult.iterations.length }} 组 ·
          通过 {{ debugResult.iterations.filter((item) => item.status === 'passed').length }} /
          失败 {{ debugResult.iterations.filter((item) => item.status !== 'passed').length }}
        </span>
      </div>
      <el-tabs v-model="responseTab" class="response-tabs">
        <el-tab-pane v-if="debugResult.iterations?.length" label="数据驱动结果" name="iterations">
          <el-table :data="debugResult.iterations" size="small" border>
            <el-table-column prop="label" label="数据集" min-width="120" />
            <el-table-column label="结果" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'passed' ? 'success' : 'danger'" size="small">
                  {{ row.status === 'passed' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="HTTP" width="80">
              <template #default="{ row }">{{ row.response_status ?? '-' }}</template>
            </el-table-column>
            <el-table-column label="耗时" width="100">
              <template #default="{ row }">{{ formatDuration(row.duration_ms) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row, $index }">
                <el-button link type="primary" @click="showIterationDetail($index)">详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane v-if="displayedDebug.pre_script_logs?.length" label="预执行日志" name="pre_logs">
          <pre class="response-pre">{{ displayedDebug.pre_script_logs.join('\n') || '-' }}</pre>
        </el-tab-pane>
        <el-tab-pane label="提取变量" name="extracted">
          <el-table
            v-if="extractedVariableRows.length"
            :data="extractedVariableRows"
            size="small"
            border
          >
            <el-table-column prop="key" label="变量名" min-width="140" />
            <el-table-column prop="value" label="提取值" min-width="240" show-overflow-tooltip />
          </el-table>
          <div v-else class="form-tip">暂无提取结果，请在后执行操作中配置提取规则后重新发送</div>
        </el-tab-pane>
        <el-tab-pane label="返回结果" name="result">
          <div v-if="activeDebugDetail?.label" class="form-tip">当前查看：{{ activeDebugDetail.label }}</div>
          <pre class="response-pre">{{ displayedDebug.response_body || displayedDebug.error_message || '-' }}</pre>
        </el-tab-pane>
        <el-tab-pane label="响应头" name="resp_headers">
          <pre class="response-pre">{{ displayedDebug.response_headers || '{}' }}</pre>
        </el-tab-pane>
        <el-tab-pane label="请求报文" name="request_msg">
          <pre class="response-pre">{{ displayedDebug.request_message || '-' }}</pre>
        </el-tab-pane>
        <el-tab-pane label="断言结果" name="assertions">
          <el-table
            v-if="displayedDebug.assertion_results?.length"
            :data="displayedDebug.assertion_results"
            size="small"
            border
          >
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column label="结果" width="80">
              <template #default="{ row }">
                <el-tag :type="row.passed ? 'success' : 'danger'" size="small">
                  {{ row.passed ? '通过' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="message" label="说明" min-width="200" show-overflow-tooltip />
          </el-table>
          <el-empty v-else description="无断言结果" :image-size="60" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="jsonImportDialogVisible" title="从 JSON 导入表单参数" width="560px" append-to-body>
      <div class="form-tip">粘贴 JSON 对象，嵌套字段（如 dataJson）会自动转为 JSON 字符串</div>
      <el-input v-model="jsonImportText" type="textarea" :rows="12" placeholder='{"key":"value"}' />
      <template #footer>
        <el-button @click="jsonImportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyJsonImport">确定</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="jsonExportDialogVisible" title="导出 JSON" width="560px" append-to-body>
      <el-input v-model="jsonExportText" type="textarea" :rows="12" readonly />
      <template #footer>
        <el-button @click="jsonExportDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyExportedJson">复制</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, DocumentChecked, MagicStick, Plus, Promotion, Upload } from '@element-plus/icons-vue'
import { apiAutomationApi } from '@/api'
import ApiKvParamTable from '@/components/ApiKvParamTable.vue'
import ApiDataDriveTable from '@/components/ApiDataDriveTable.vue'
import ApiCaseOperationList from '@/components/ApiCaseOperationList.vue'
import {
  DEFAULT_ASSERTIONS,
  emptyKvRow,
  emptyDataDriveRow,
  ensureKvRows,
  parseCaseConfig,
  serializeCaseConfig,
  splitUrlForEditor,
  displayUrlFromSplit,
  enrichHeaderRows,
  countActiveKvRows,
  jsonToFormBodyRows,
  formRowsToJson,
  emptyBodyStores,
  activePreScript,
  variablesMapFromRows,
  syncLegacyFromOperations,
  operationHasContent,
} from '@/utils/apiCaseConfig'

const props = defineProps({
  suiteId: { type: Number, default: null },
  caseData: { type: Object, default: null },
  environments: { type: Array, default: () => [] },
  suiteEnvironmentId: { type: Number, default: null },
  caseCount: { type: Number, default: 0 },
})

const emit = defineEmits(['saved', 'new', 'import'])

const methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
const activeTab = ref('headers')
const responseTab = ref('result')
const formRef = ref()
const saving = ref(false)
const copying = ref(false)
const sending = ref(false)
const aiGenerating = ref(false)
const debugResult = ref(null)
const headerRows = ref([emptyKvRow()])
const queryRows = ref([emptyKvRow()])
const pathRows = ref([emptyKvRow()])
const cookieRows = ref([emptyKvRow()])
const variableRows = ref([emptyKvRow()])
const dataDriveEnabled = ref(false)
const dataDriveRows = ref([emptyDataDriveRow()])
const preOperations = ref([])
const postOperations = ref([])
const dataDriveRunMode = ref('all')
const activeDebugDetail = ref(null)
const bodyStores = reactive(emptyBodyStores())
const editingId = ref(null)
const jsonImportDialogVisible = ref(false)
const jsonImportText = ref('')
const jsonExportDialogVisible = ref(false)
const jsonExportText = ref('')
const suppressBodyTypeWatch = ref(false)
const preScriptDebuggingId = ref('')
const preScriptDebuggingLoading = ref(false)
const preScriptDebugResult = ref(null)
const postScriptDebuggingId = ref('')
const postScriptDebuggingLoading = ref(false)
const postScriptDebugResult = ref(null)

const form = reactive({
  name: '',
  environment_id: null,
  method: 'GET',
  full_url: '',
  body_type: 'none',
  auth: { type: 'none', token: '', username: '', password: '' },
  assertions: DEFAULT_ASSERTIONS,
  sort_order: 0,
  enabled: true,
})

const rules = {
  name: [{ required: true, message: '请输入用例名称', trigger: 'blur' }],
}

const selectedEnv = computed(() =>
  props.environments.find((e) => e.id === form.environment_id) || null
)

const canSend = computed(
  () => props.suiteId && form.environment_id && form.full_url.trim() && form.method
)

const canAiGenerateData = computed(
  () => props.suiteId && form.method && (form.full_url.trim() || form.name.trim())
)

const activeQueryCount = computed(() => countActiveKvRows(queryRows.value))
const activePathCount = computed(() => countActiveKvRows(pathRows.value))
const activeCookieCount = computed(() => countActiveKvRows(cookieRows.value))
const activeVariableCount = computed(() => {
  const base = countActiveKvRows(variableRows.value)
  if (!dataDriveEnabled.value) return base
  const dataCount = dataDriveRows.value.filter(
    (row) =>
      row.enabled !== false &&
      (row.name?.trim() || Object.values(row.values || {}).some((v) => String(v ?? '').trim()))
  ).length
  return base + dataCount
})

const hasConfiguredPreOperations = computed(() =>
  preOperations.value.some((item) => operationHasContent({ ...item, enabled: true }))
)

const hasConfiguredPostOperations = computed(() =>
  postOperations.value.some((item) => operationHasContent({ ...item, enabled: true }))
)

const enabledDataDriveRows = computed(() =>
  dataDriveRows.value.filter(
    (row) =>
      row.enabled !== false &&
      (row.name?.trim() || Object.values(row.values || {}).some((v) => String(v ?? '').trim()))
  )
)

const showDataDriveSelector = computed(
  () => dataDriveEnabled.value && enabledDataDriveRows.value.length > 1
)

const dataDriveRunOptions = computed(() => {
  const options = enabledDataDriveRows.value.map((row, index) => ({
    label: row.name?.trim() || `数据集${index + 1}`,
    value: index,
  }))
  options.push({ label: '全部运行', value: 'all' })
  return options
})

const sendButtonLabel = computed(() =>
  showDataDriveSelector.value && dataDriveRunMode.value === 'all' ? '全部发送' : '发送'
)

const preScriptVariableRows = computed(() => {
  const vars = preScriptDebugResult.value?.variables || {}
  return Object.entries(vars).map(([key, value]) => ({ key, value }))
})

const postScriptVariableRows = computed(() => {
  const vars = postScriptDebugResult.value?.variables || {}
  return Object.entries(vars).map(([key, value]) => ({ key, value }))
})

const displayedDebug = computed(() => activeDebugDetail.value || debugResult.value)

const extractedVariableRows = computed(() => {
  const vars = displayedDebug.value?.extracted_variables || {}
  return Object.entries(vars).map(([key, value]) => ({ key, value }))
})
const activeHeaderCount = computed(() => countActiveKvRows(headerRows.value))
const activeBodyCount = computed(() => {
  const type = form.body_type
  if (type === 'form-data') return countActiveKvRows(bodyStores.formData)
  if (type === 'urlencoded') return countActiveKvRows(bodyStores.urlencoded)
  if (type === 'json') return bodyStores.json?.trim() ? 1 : 0
  if (type === 'raw') return bodyStores.raw?.trim() ? 1 : 0
  return 0
})

const currentFormBodyRows = computed({
  get() {
    return form.body_type === 'form-data' ? bodyStores.formData : bodyStores.urlencoded
  },
  set(value) {
    if (form.body_type === 'form-data') {
      bodyStores.formData = value
    } else {
      bodyStores.urlencoded = value
    }
  },
})

function resetBodyStores() {
  Object.assign(bodyStores, emptyBodyStores())
  bodyStores.urlencoded = [emptyKvRow()]
  bodyStores.formData = [emptyKvRow()]
}

function formatDuration(ms) {
  if (!ms && ms !== 0) return '-'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function buildDisplayUrl(env, path) {
  if (!path) return env?.base_url || ''
  let segment = path
  if (path.startsWith('http://') || path.startsWith('https://')) {
    try {
      const parsed = new URL(path)
      segment = `${parsed.pathname}${parsed.search}`
    } catch {
      return path
    }
  }
  const normalized = segment.startsWith('/') ? segment : `/${segment}`
  const base = (env?.base_url || '').replace(/\/$/, '')
  return base ? `${base}${normalized}` : normalized
}

function pathFromFullUrl(fullUrl, env) {
  const text = (fullUrl || '').trim()
  if (!text) return '/'
  try {
    if (text.includes('://')) {
      const parsed = new URL(text)
      return `${parsed.pathname}${parsed.search}`
    }
    const base = env?.base_url ? new URL(env.base_url) : null
    if (base) {
      const parsed = new URL(text, env.base_url)
      if (parsed.origin === base.origin) {
        return `${parsed.pathname}${parsed.search}`
      }
    }
    return text
  } catch {
    return text
  }
}

function syncQueryFromUrl() {
  const url = form.full_url?.trim()
  if (!url || !url.includes('?')) return
  const split = splitUrlForEditor(url, selectedEnv.value)
  if (split.queryRows.some((r) => r.key?.trim())) {
    queryRows.value = split.queryRows
    form.full_url = displayUrlFromSplit(split, selectedEnv.value)
    if (split.pathRows.some((r) => r.key?.trim())) {
      pathRows.value = split.pathRows
    }
  }
}

function onUrlPaste() {
  setTimeout(() => syncQueryFromUrl(), 0)
}

function syncContentTypeHeader(bodyType) {
  const map = {
    json: 'application/json',
    urlencoded: 'application/x-www-form-urlencoded',
    'form-data': 'multipart/form-data',
  }
  const contentType = map[bodyType]
  const idx = headerRows.value.findIndex((r) => r.key?.toLowerCase() === 'content-type')
  if (!contentType) {
    if (idx >= 0) headerRows.value.splice(idx, 1)
    return
  }
  const row = { key: 'Content-Type', value: contentType, enabled: true, desc: '' }
  if (idx >= 0) {
    headerRows.value[idx] = { ...headerRows.value[idx], ...row }
  } else {
    headerRows.value.push(row)
  }
}

function openJsonImport() {
  jsonImportText.value = ''
  jsonImportDialogVisible.value = true
}

function applyJsonImport() {
  try {
    const rows = jsonToFormBodyRows(jsonImportText.value)
    if (form.body_type === 'form-data') {
      bodyStores.formData = rows
    } else {
      bodyStores.urlencoded = rows
    }
    jsonImportDialogVisible.value = false
    ElMessage.success('已导入表单参数')
  } catch (error) {
    ElMessage.error(error.message || 'JSON 格式不正确')
  }
}

function handleExportJson() {
  const rows = currentFormBodyRows.value.filter((r) => r.enabled !== false && r.key?.trim())
  if (!rows.length) {
    ElMessage.warning('没有可导出的参数')
    return
  }
  jsonExportText.value = formRowsToJson(rows)
  jsonExportDialogVisible.value = true
}

async function copyExportedJson() {
  try {
    await navigator.clipboard.writeText(jsonExportText.value)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

function syncEnvHeaders() {
  const env = selectedEnv.value
  if (form.full_url && env) {
    const pathOnly = pathFromFullUrl(form.full_url, env).split('?')[0]
    form.full_url = buildDisplayUrl(env, pathOnly)
  }
}

function formatBodyText(bodyText, bodyType) {
  const text = bodyText || ''
  if (!text.trim() || bodyType !== 'json') return text
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return text
  }
}

function loadConfigFromCase(caseRow) {
  suppressBodyTypeWatch.value = true
  const config = parseCaseConfig(caseRow?.headers, caseRow?.body, caseRow?.assertions || DEFAULT_ASSERTIONS)
  headerRows.value = config.headerRows
  queryRows.value = config.queryRows
  pathRows.value = config.pathRows
  cookieRows.value = config.cookieRows
  variableRows.value = config.variableRows
  dataDriveEnabled.value = config.dataDriveEnabled
  dataDriveRows.value = config.dataDriveRows
  preOperations.value = config.preOperations
  postOperations.value = config.postOperations
  dataDriveRunMode.value = 'all'
  form.auth = { ...form.auth, ...config.auth }

  resetBodyStores()
  Object.assign(bodyStores, config.bodyStores)
  bodyStores.urlencoded = ensureKvRows(config.bodyStores.urlencoded)
  bodyStores.formData = ensureKvRows(config.bodyStores.formData)
  if (config.bodyType === 'json' && bodyStores.json) {
    bodyStores.json = formatBodyText(bodyStores.json, 'json')
  }
  form.body_type = config.bodyType
  suppressBodyTypeWatch.value = false
}

function resetForm(caseRow = null) {
  suppressBodyTypeWatch.value = true
  debugResult.value = null
  activeDebugDetail.value = null
  preScriptDebugResult.value = null
  postScriptDebugResult.value = null
  editingId.value = caseRow?.id || null
  const envId = props.suiteEnvironmentId || props.environments[0]?.id || null
  form.environment_id = envId

  if (!caseRow) {
    form.name = ''
    form.method = 'GET'
    form.full_url = buildDisplayUrl(selectedEnv.value, '/')
    form.body_type = 'none'
    resetBodyStores()
    form.auth = { type: 'none', token: '', username: '', password: '' }
    form.assertions = DEFAULT_ASSERTIONS
    preOperations.value = []
    postOperations.value = []
    form.sort_order = props.caseCount
    form.enabled = true
    headerRows.value = [emptyKvRow()]
    queryRows.value = [emptyKvRow()]
    pathRows.value = [emptyKvRow()]
    cookieRows.value = [emptyKvRow()]
    variableRows.value = [emptyKvRow()]
    dataDriveEnabled.value = false
    dataDriveRows.value = [emptyDataDriveRow()]
    dataDriveRunMode.value = 'all'
    activeTab.value = 'headers'
    suppressBodyTypeWatch.value = false
    return
  }

  form.name = caseRow.name || ''
  form.method = caseRow.method || 'GET'
  const pathOnly = pathFromFullUrl(caseRow.path || '/', selectedEnv.value).split('?')[0]
  const split = splitUrlForEditor(buildDisplayUrl(selectedEnv.value, pathOnly), selectedEnv.value)
  form.full_url = displayUrlFromSplit(split, selectedEnv.value)
  form.assertions = caseRow.assertions || DEFAULT_ASSERTIONS
  form.sort_order = caseRow.sort_order ?? 0
  form.enabled = caseRow.enabled ?? true
  loadConfigFromCase(caseRow)
  if (split.queryRows.some((r) => r.key?.trim())) {
    queryRows.value = split.queryRows
  }
  if (split.pathRows.some((r) => r.key?.trim())) {
    pathRows.value = split.pathRows
  }
  if (caseRow.body?.trim() || countActiveKvRows(bodyStores.urlencoded) || countActiveKvRows(bodyStores.formData)) {
    activeTab.value = 'body'
  }
  suppressBodyTypeWatch.value = false
}

function handleNew() {
  emit('new')
  resetForm(null)
}

function buildCasePayload() {
  const pathOnly = pathFromFullUrl(form.full_url, selectedEnv.value).split('?')[0]
  const synced = syncLegacyFromOperations(preOperations.value, postOperations.value)
  const serialized = serializeCaseConfig({
    headerRows: headerRows.value,
    queryRows: queryRows.value,
    pathRows: pathRows.value,
    cookieRows: cookieRows.value,
    variableRows: variableRows.value,
    dataDriveEnabled: dataDriveEnabled.value,
    dataDriveRows: dataDriveRows.value,
    extractRows: synced.extractRows,
    auth: form.auth,
    bodyType: form.body_type,
    bodyStores,
    preOperations: preOperations.value,
    postOperations: postOperations.value,
    path: pathOnly,
  })
  return {
    name: form.name,
    method: form.method,
    path: serialized.path,
    headers: serialized.headers,
    body: serialized.body,
    assertions: synced.assertions,
    sort_order: form.sort_order,
    enabled: form.enabled,
  }
}

function applyGeneratedParams(rows, generated) {
  if (!generated?.length) return
  const map = Object.fromEntries(generated.map((item) => [item.key, item.value]))
  rows.forEach((row) => {
    if (row.key && Object.prototype.hasOwnProperty.call(map, row.key)) {
      row.value = map[row.key]
    }
  })
}

function applyGeneratedBody(bodyText) {
  if (!bodyText) return
  if (form.body_type === 'json') {
    bodyStores.json = formatBodyText(bodyText, 'json')
    return
  }
  if (form.body_type === 'raw') {
    bodyStores.raw = bodyText
    return
  }
  if (form.body_type === 'form-data' || form.body_type === 'urlencoded') {
    try {
      const rows = JSON.parse(bodyText)
      if (!Array.isArray(rows)) return
      const mapped = rows.map((row) => ({
        key: row.key || '',
        value: row.value || '',
        enabled: row.enabled !== false,
        desc: row.desc || '',
      }))
      if (form.body_type === 'form-data') {
        bodyStores.formData = ensureKvRows(mapped)
      } else {
        bodyStores.urlencoded = ensureKvRows(mapped)
      }
    } catch {
      // ignore invalid generated body
    }
  }
}

async function handleAiGenerateData() {
  if (!canAiGenerateData.value) return
  aiGenerating.value = true
  try {
    const payload = buildCasePayload()
    const pathOnly = pathFromFullUrl(form.full_url, selectedEnv.value).split('?')[0]
    const data = await apiAutomationApi.generateCaseData({
      name: form.name,
      method: form.method,
      path: pathOnly || payload.path || '/',
      url: form.full_url,
      body: payload.body,
      body_type: form.body_type,
      headers: payload.headers,
      query_params: queryRows.value.filter((row) => row.key?.trim()),
      path_params: pathRows.value.filter((row) => row.key?.trim()),
    })
    applyGeneratedBody(data.body)
    applyGeneratedParams(queryRows.value, data.query)
    applyGeneratedParams(pathRows.value, data.path)
    if (data.body || data.query?.length || data.path?.length) {
      activeTab.value = 'body'
      ElMessage.success(data.message || 'AI 生成成功')
    } else {
      ElMessage.warning('未生成可填充的数据')
    }
  } finally {
    aiGenerating.value = false
  }
}

async function handlePreScriptDebug(operation) {
  const script = activePreScript(operation.stores, operation.lang)
  if (!script?.trim()) {
    ElMessage.warning('请先编写预执行脚本')
    return
  }
  preScriptDebuggingId.value = operation.id
  preScriptDebugResult.value = null
  preScriptDebuggingLoading.value = true
  try {
    preScriptDebugResult.value = await apiAutomationApi.debugPreScript({
      script,
      language: operation.lang,
      variables: variablesMapFromRows(variableRows.value),
    })
    if (preScriptDebugResult.value.status === 'passed') {
      ElMessage.success('预执行脚本调试成功')
    } else {
      ElMessage.error(preScriptDebugResult.value.error_message || '预执行脚本调试失败')
    }
  } finally {
    preScriptDebuggingLoading.value = false
  }
}

function parseDebugResponseHeaders(debug) {
  const raw = debug?.response_headers
  if (!raw) return {}
  if (typeof raw === 'object') return raw
  try {
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed !== null ? parsed : {}
  } catch {
    return {}
  }
}

async function handlePostScriptDebug(operation) {
  const script = activePreScript(operation.stores, operation.lang)
  if (!script?.trim()) {
    ElMessage.warning('请先编写后置脚本')
    return
  }
  const debug = displayedDebug.value || debugResult.value
  postScriptDebuggingId.value = operation.id
  postScriptDebugResult.value = null
  postScriptDebuggingLoading.value = true
  try {
    postScriptDebugResult.value = await apiAutomationApi.debugPostScript({
      script,
      language: operation.lang,
      variables: variablesMapFromRows(variableRows.value),
      response_body: debug?.response_body || '',
      response_status: debug?.response_status ?? null,
      response_headers: parseDebugResponseHeaders(debug),
    })
    if (postScriptDebugResult.value.status === 'passed') {
      ElMessage.success('后置脚本调试成功')
    } else {
      ElMessage.error(postScriptDebugResult.value.error_message || '后置脚本调试失败')
    }
  } finally {
    postScriptDebuggingLoading.value = false
  }
}

async function handleSave() {
  if (!props.suiteId) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    if (props.suiteEnvironmentId !== form.environment_id) {
      await apiAutomationApi.updateSuite(props.suiteId, { environment_id: form.environment_id })
    }

    const payload = buildCasePayload()
    if (editingId.value) {
      await apiAutomationApi.updateCase(editingId.value, payload)
      ElMessage.success('用例已保存')
    } else {
      const created = await apiAutomationApi.createCase({ ...payload, suite_id: props.suiteId })
      editingId.value = created.id
      ElMessage.success('用例已创建')
    }
    emit('saved', editingId.value)
  } finally {
    saving.value = false
  }
}

async function handleCopy() {
  if (!editingId.value || !props.suiteId) return
  copying.value = true
  try {
    if (formRef.value) {
      try {
        await formRef.value.validate()
      } catch {
        ElMessage.warning('请先完善并保存当前用例后再复制')
        return
      }
    }
    await apiAutomationApi.updateCase(editingId.value, buildCasePayload())
    const copied = await apiAutomationApi.copyCase(editingId.value)
    ElMessage.success('用例已复制')
    emit('saved', copied.id)
  } finally {
    copying.value = false
  }
}

async function handleSend() {
  if (!canSend.value) return
  sending.value = true
  debugResult.value = null
  activeDebugDetail.value = null
  preScriptDebugResult.value = null
  postScriptDebugResult.value = null
  try {
    const payload = buildCasePayload()
    const debugPayload = {
      environment_id: form.environment_id,
      method: payload.method,
      path: payload.path,
      headers: payload.headers,
      body: payload.body,
      assertions: payload.assertions,
    }
    if (showDataDriveSelector.value) {
      if (dataDriveRunMode.value === 'all') {
        debugPayload.run_all_data_sets = true
      } else {
        debugPayload.data_drive_index = dataDriveRunMode.value
      }
    }
    debugResult.value = await apiAutomationApi.debugCase(debugPayload)
    if (debugResult.value.extracted_variables && Object.keys(debugResult.value.extracted_variables).length) {
      responseTab.value = 'extracted'
    } else {
      responseTab.value = debugResult.value.iterations?.length ? 'iterations' : 'result'
    }
  } finally {
    sending.value = false
  }
}

function showIterationDetail(index) {
  activeDebugDetail.value = debugResult.value?.iterations?.[index] || null
  responseTab.value = 'result'
}

function applyCaptureItem(item) {
  form.name = item.name || form.name
  form.method = item.method || 'GET'
  form.full_url = buildDisplayUrl(selectedEnv.value, item.path || item.full_url)
  const config = parseCaseConfig(item.headers, item.body, item.assertions || DEFAULT_ASSERTIONS)
  headerRows.value = config.headerRows
  form.auth = { ...form.auth, ...config.auth }
  resetBodyStores()
  Object.assign(bodyStores, config.bodyStores)
  bodyStores.urlencoded = ensureKvRows(config.bodyStores.urlencoded)
  bodyStores.formData = ensureKvRows(config.bodyStores.formData)
  if (bodyStores.json) {
    bodyStores.json = formatBodyText(bodyStores.json, 'json')
  }
  form.body_type = config.bodyType !== 'none' ? config.bodyType : (bodyStores.json ? 'json' : 'none')
  form.assertions = item.assertions || DEFAULT_ASSERTIONS
  preOperations.value = config.preOperations
  postOperations.value = config.postOperations
  syncQueryFromUrl()
  if (activeBodyCount.value > 0) {
    activeTab.value = 'body'
  } else if (queryRows.value.some((r) => r.key?.trim())) {
    activeTab.value = 'query'
  } else {
    activeTab.value = 'headers'
  }
}

watch(
  () => form.body_type,
  (type) => {
    if (suppressBodyTypeWatch.value) return
    syncContentTypeHeader(type)
  }
)

watch(
  () => [props.caseData, props.suiteEnvironmentId, props.environments.length],
  () => {
    resetForm(props.caseData)
  },
  { immediate: true }
)

defineExpose({ resetForm, applyCaptureItem, handleNew })
</script>

<style scoped>
.api-case-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 520px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #ebeef5;
  background: #fafafa;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.env-label {
  font-size: 13px;
  color: #606266;
}

.editor-main {
  flex: 1;
  padding: 16px;
  overflow: auto;
}

.name-form-item {
  margin-bottom: 0;
  width: 100%;
}

.name-form-item :deep(.el-form-item__content) {
  margin-left: 0 !important;
}

.name-row {
  margin-bottom: 12px;
}

.url-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.method-select {
  width: 110px;
  flex-shrink: 0;
}

.url-input {
  flex: 1;
}

.request-tabs {
  margin-top: 4px;
}

.apipost-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.apipost-tabs :deep(.el-tabs__content) {
  padding-top: 12px;
}

.apipost-tabs :deep(.el-tabs__item) {
  font-size: 13px;
  padding: 0 16px;
  height: 36px;
}

.apipost-tabs :deep(.el-tabs__item.is-active) {
  color: #e6a23c;
  font-weight: 600;
}

.apipost-tabs :deep(.el-tabs__active-bar) {
  background-color: #e6a23c;
}

.tab-with-dot {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.tab-config-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #67c23a;
}

.path-tip {
  margin-bottom: 8px;
}

.auth-form {
  max-width: 520px;
  padding-top: 8px;
}

.script-editor {
  font-family: Consolas, Monaco, monospace;
}

.pre-script-debug-result {
  margin-top: 12px;
  padding: 12px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.pre-debug-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.pre-debug-error {
  font-size: 12px;
  color: #f56c6c;
}

.pre-debug-block {
  margin-top: 10px;
}

.script-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 0;
}

.script-hints {
  margin-top: 8px;
}

.script-hint-pre {
  margin: 4px 0 8px;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  color: #606266;
}

.script-example {
  white-space: pre-wrap;
}

.script-editor {
  font-family: Consolas, Monaco, monospace;
}

.post-script-hidden {
  display: none;
}

.assertions-block {
  margin-top: 16px;
}

.block-label {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}

.settings-inline {
  margin-top: 0;
  align-items: center;
  width: 100%;
}

.post-settings-row {
  margin-top: 0;
}

.enable-col {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.operation-footer :deep(.settings-inline) {
  margin-top: 0;
}

.inline-label {
  margin-right: 8px;
  font-size: 13px;
  color: #606266;
}

.kv-toolbar {
  margin-bottom: 8px;
}

.kv-table {
  width: 100%;
}

.body-type-group {
  margin-bottom: 8px;
}

.body-editor-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.body-editor-toolbar {
  display: flex;
  justify-content: flex-end;
}

.body-editor {
  font-family: Consolas, Monaco, monospace;
}

.form-tip {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
}

.section-label {
  margin: 12px 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.extract-collapse {
  margin-top: 12px;
  border: none;
}

.extract-collapse :deep(.el-collapse-item__header) {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  border-bottom: none;
  height: 40px;
  line-height: 40px;
}

.extract-collapse :deep(.el-collapse-item__wrap) {
  border-bottom: none;
}

.extract-collapse-title {
  margin-right: 8px;
}

.extract-count-tag {
  font-weight: normal;
}

.data-drive-section {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px dashed #ebeef5;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.editor-response {
  border-top: 1px solid #ebeef5;
  background: #fcfcfc;
  max-height: 280px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.response-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  border-bottom: 1px solid #ebeef5;
}

.response-meta {
  font-size: 12px;
  color: #606266;
}

.response-tabs {
  flex: 1;
  overflow: hidden;
  padding: 0 16px 12px;
}

.response-tabs :deep(.el-tabs__content) {
  max-height: 180px;
  overflow: auto;
}

.response-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 12px;
  line-height: 1.5;
  font-family: Consolas, Monaco, monospace;
}
</style>

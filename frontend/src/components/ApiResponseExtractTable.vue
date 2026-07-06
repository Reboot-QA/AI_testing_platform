<template>
  <div class="response-extract-table">
    <div class="extract-source-bar">
      <span class="source-label">提取来源</span>
      <el-select v-model="extractSource" size="small" class="source-select" @change="handleSourceChange">
        <el-option
          v-for="item in EXTRACT_SOURCE_OPTIONS"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
      <span v-if="extractSource === 'response_json'" class="source-tip">XML(类XML)会智能转 JSON</span>
    </div>

    <div v-if="showPathGenerator" class="path-generator">
      <div class="generator-header">
        <span class="generator-title">表达式生成</span>
        <span class="generator-tip">请粘贴<strong>响应体</strong> JSON（不是请求体），或点击「填入最近响应」</span>
      </div>

      <el-alert
        v-if="showRequestBodyWarning"
        type="warning"
        :closable="false"
        show-icon
        title="检测到粘贴内容更像请求体，提取规则应对响应 JSON 生成，请点击「填入最近响应」"
        class="request-warning"
      />

      <div class="generator-step">
        <span class="step-label">1. 返回 JSON</span>
        <div class="response-input-wrap">
          <el-input
            v-model="responseJsonText"
            type="textarea"
            :rows="5"
            placeholder='粘贴接口返回，如 {"code":9999,"msg":"内部异常","data":{...}}'
            class="response-textarea"
          />
          <el-button size="small" :disabled="!props.responseBody?.trim()" @click="fillFromLastResponse">
            填入最近响应
          </el-button>
        </div>
      </div>

      <div class="generator-step field-step">
        <span class="step-label">2. 提取字段</span>
        <el-input
          v-model="fieldInput"
          size="small"
          class="field-input"
          placeholder="输入字段名，如 msg / code / token"
          clearable
          @keyup.enter="applyGeneratedRow"
        />
        <el-button size="small" type="primary" plain :disabled="!canGenerate" @click="generatePreview">
          生成表达式
        </el-button>
        <el-button size="small" type="primary" :disabled="!canAdd" @click="applyGeneratedRow">
          生成并添加
        </el-button>
      </div>

      <div v-if="generatedPreview.path" class="generated-result">
        <span>JSON Path：</span>
        <code>{{ generatedPreview.path }}</code>
        <span v-if="generatedPreview.previewValue" class="preview-value">
          · 值：{{ truncatePreview(generatedPreview.previewValue) }}
        </span>
      </div>
      <div v-else-if="generateError" class="generated-error">{{ generateError }}</div>
    </div>

    <div class="extract-table-head">提取变量</div>
    <div class="kv-toolbar">
      <el-button size="small" @click="addRow">添加提取</el-button>
      <el-button size="small" type="danger" plain :disabled="!selectedIndexes.size" @click="batchDelete">
        批量删除
      </el-button>
    </div>
    <el-table :data="rows" size="small" border class="kv-table">
      <el-table-column width="44" align="center">
        <template #header>
          <el-checkbox v-model="allSelected" :indeterminate="indeterminate" />
        </template>
        <template #default="{ $index }">
          <el-checkbox :model-value="isSelected($index)" @change="(val) => toggleSelect($index, val)" />
        </template>
      </el-table-column>
      <el-table-column label="启用" width="60" align="center">
        <template #default="{ row }">
          <el-checkbox v-model="row.enabled" />
        </template>
      </el-table-column>
      <el-table-column label="变量名" min-width="120">
        <template #default="{ row }">
          <el-input v-model="row.key" placeholder="access_token" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="变量类型" width="130">
        <template #default="{ row }">
          <el-select v-model="row.scope" size="small">
            <el-option
              v-for="item in VARIABLE_SCOPE_OPTIONS"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column :label="pathColumnLabel" min-width="180">
        <template #default="{ row }">
          <el-input
            v-model="row.path"
            :placeholder="pathPlaceholder"
            :disabled="!extractRowNeedsPath(extractSource)"
            size="small"
          />
        </template>
      </el-table-column>
      <el-table-column label="说明" min-width="100">
        <template #default="{ row }">
          <el-input v-model="row.desc" placeholder="备注" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60" align="center">
        <template #default="{ $index }">
          <el-button link type="danger" @click="removeRow($index)">删</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  buildExtractExpression,
  emptyExtractRow,
  extractRowNeedsPath,
  getExtractSourceMeta,
  jsonPathExists,
  looksLikeRequestBody,
  normalizeExtractSource,
  normalizeJsonText,
  EXTRACT_SOURCE_OPTIONS,
  VARIABLE_SCOPE_OPTIONS,
} from '@/utils/apiCaseConfig'

const rows = defineModel('rows', { type: Array, required: true })
const extractSource = defineModel('source', { type: String, default: 'response_json' })
const props = defineProps({
  responseBody: { type: String, default: '' },
})

const responseJsonText = ref('')
const fieldInput = ref('')
const generatedPreview = ref({ path: '', variableName: '', matched: false, previewValue: '' })
const generateError = ref('')
const selectedIndexes = ref(new Set())

const canGenerate = computed(
  () => responseJsonText.value.trim() && fieldInput.value.trim()
)

const canAdd = computed(() => canGenerate.value)

const showRequestBodyWarning = computed(() => {
  if (!responseJsonText.value.trim()) return false
  try {
    return looksLikeRequestBody(JSON.parse(responseJsonText.value))
  } catch {
    return false
  }
})

const responseJsonOutdated = computed(() => {
  if (!props.responseBody?.trim() || !responseJsonText.value.trim()) return false
  return normalizeJsonText(props.responseBody) !== normalizeJsonText(responseJsonText.value)
})

const allSelected = computed({
  get() {
    return rows.value.length > 0 && selectedIndexes.value.size === rows.value.length
  },
  set(val) {
    selectedIndexes.value = val ? new Set(rows.value.map((_, index) => index)) : new Set()
  },
})

const indeterminate = computed(() => {
  const size = selectedIndexes.value.size
  return size > 0 && size < rows.value.length
})

function truncatePreview(text) {
  const value = String(text ?? '')
  return value.length > 60 ? `${value.slice(0, 60)}...` : value
}

function setResponseJson(text) {
  try {
    responseJsonText.value = JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    responseJsonText.value = text
  }
}

function fillFromLastResponse() {
  if (!props.responseBody?.trim()) {
    ElMessage.warning('暂无最近响应，请先发送请求')
    return
  }
  setResponseJson(props.responseBody)
  generatedPreview.value = { path: '', variableName: '', matched: false, previewValue: '' }
  generateError.value = ''
  ElMessage.success('已填入最近响应体')
}

function validateAgainstLatestResponse(path, fieldName) {
  if (!props.responseBody?.trim()) return true
  try {
    const parsed = JSON.parse(props.responseBody)
    if (jsonPathExists(parsed, path)) return true
    ElMessage.error(`字段「${fieldName}」在最近响应中不存在（${path}），请基于响应 JSON 重新生成`)
    return false
  } catch {
    return true
  }
}

function generatePreview() {
  generateError.value = ''
  if (responseJsonOutdated.value) {
    ElMessage.warning('粘贴内容与最近响应不一致，建议点击「填入最近响应」后再生成')
  }
  try {
    generatedPreview.value = buildExtractExpression(fieldInput.value, responseJsonText.value)
  } catch (err) {
    generatedPreview.value = { path: '', variableName: '', matched: false, previewValue: '' }
    generateError.value = err.message || '生成失败'
  }
}

function isSelected(index) {
  return selectedIndexes.value.has(index)
}

function toggleSelect(index, checked) {
  const next = new Set(selectedIndexes.value)
  if (checked) next.add(index)
  else next.delete(index)
  selectedIndexes.value = next
}

const showPathGenerator = computed(
  () => normalizeExtractSource(extractSource.value) === 'response_json'
)

const pathColumnLabel = computed(() => getExtractSourceMeta(extractSource.value).pathLabel)

const pathPlaceholder = computed(() => getExtractSourceMeta(extractSource.value).placeholder)

function handleSourceChange() {
  extractSource.value = normalizeExtractSource(extractSource.value)
  if (!extractRowNeedsPath(extractSource.value)) {
    rows.value.forEach((row) => {
      row.path = ''
    })
  }
}

function addRow() {
  rows.value.push(emptyExtractRow())
}

function removeRow(index) {
  rows.value.splice(index, 1)
  if (!rows.value.length) {
    rows.value.push(emptyExtractRow())
  }
}

function batchDelete() {
  rows.value = rows.value.filter((_, index) => !selectedIndexes.value.has(index))
  selectedIndexes.value = new Set()
  if (!rows.value.length) {
    rows.value.push(emptyExtractRow())
  }
}

function applyGeneratedRow() {
  try {
    const result = buildExtractExpression(fieldInput.value, responseJsonText.value)
    if (!validateAgainstLatestResponse(result.path, result.variableName)) return

    rows.value.push({
      key: result.variableName,
      path: result.path,
      enabled: true,
      desc: '表达式生成器',
      scope: 'environment',
    })
    ElMessage.success(`已添加 ${result.path}`)
    fieldInput.value = ''
    generatedPreview.value = { path: '', variableName: '', matched: false, previewValue: '' }
    generateError.value = ''
  } catch (err) {
    generateError.value = err.message || '生成失败'
    ElMessage.error(err.message || '生成失败')
  }
}
</script>

<style scoped>
.extract-source-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  padding: 10px 12px;
  background: #fafafa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.source-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.source-select {
  width: 180px;
}

.source-tip {
  font-size: 12px;
  color: #909399;
}

.extract-table-head {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.path-generator {
  margin-bottom: 12px;
  padding: 12px;
  background: #f8fafc;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.generator-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.generator-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.generator-tip {
  font-size: 12px;
  color: #909399;
}

.request-warning {
  margin-bottom: 10px;
}

.generator-step {
  margin-bottom: 10px;
}

.field-step {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.step-label {
  font-size: 12px;
  color: #606266;
  min-width: 72px;
}

.response-input-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.response-textarea :deep(textarea) {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
}

.field-input {
  width: 220px;
}

.generated-result {
  font-size: 12px;
  color: #606266;
  padding: 8px 10px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.generated-result code {
  color: #409eff;
  font-weight: 600;
}

.preview-value {
  color: #67c23a;
}

.generated-error {
  font-size: 12px;
  color: #f56c6c;
  padding: 6px 0;
}

.kv-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.kv-table {
  width: 100%;
}
</style>

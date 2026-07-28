<template>
  <div class="requirement-docs">
    <div class="docs-grid">
      <!-- 左侧：上传与配置 -->
      <div class="panel config-panel">
        <div class="panel-h">
          <span class="panel-title">
            <el-icon><Document /></el-icon>
            上传需求文档
          </span>
        </div>
        <div class="panel-body">
          <el-form label-width="72px" class="docs-form">
            <el-form-item v-if="!scoped" label="项目">
              <el-select v-model="projectId" filterable placeholder="选择项目" style="width: 100%">
                <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="大模型">
              <el-select
                v-model="providerId"
                placeholder="请选择大模型"
                style="width: 100%"
                :loading="providersLoading"
                :disabled="!llmProviders.length"
              >
                <template #label>
                  <LlmProviderLabel
                    v-if="selectedProvider"
                    :text="formatLlmProviderLabel(selectedProvider)"
                  />
                </template>
                <el-option
                  v-for="item in llmProviders"
                  :key="item.id"
                  :label="formatLlmProviderLabel(item)"
                  :value="item.id"
                >
                  <LlmProviderLabel :text="formatLlmProviderLabel(item)" />
                </el-option>
              </el-select>
              <div v-if="!providersLoading && !llmProviders.length" class="form-tip">
                暂无可用模型，请前往
                <el-button link type="primary" @click="$router.push('/system/settings')">
                  系统管理
                </el-button>
                添加配置
              </div>
            </el-form-item>
            <el-form-item label="文档文件">
              <el-upload
                ref="uploadRef"
                class="docs-upload"
                drag
                :auto-upload="false"
                :limit="1"
                :show-file-list="false"
                :disabled="extracting"
                accept=".txt,.md,.docx"
                :on-change="handleFileChange"
                :on-remove="handleFileRemove"
                :on-exceed="handleExceed"
              >
                <el-icon class="upload-icon"><UploadFilled /></el-icon>
                <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
                <template #tip>
                  <div class="upload-tip">支持 .txt / .md / .docx，不超过 50M</div>
                </template>
              </el-upload>
              <div v-if="selectedFile" class="file-chip">
                <el-icon><Document /></el-icon>
                <span class="file-chip-name" :title="selectedFile.name">{{
                  selectedFile.name
                }}</span>
                <el-tag size="small" type="info">{{ formatFileSize(selectedFile.size) }}</el-tag>
              </div>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                class="extract-btn"
                :loading="extracting"
                :disabled="!projectId || !selectedFile"
                @click="handleExtract"
              >
                <el-icon><MagicStick /></el-icon>
                {{ extracting ? '正在解析，请稍候...' : 'AI 解析需求点' }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert
            class="mode-alert"
            :title="
              mockMode
                ? '当前为 Mock 模式，将使用本地规则提取需求点'
                : '未配置 API Key 的模型无法解析，请先在系统管理中配置 Key 或开启 Mock 模式'
            "
            type="info"
            :closable="false"
            show-icon
          />
        </div>
      </div>

      <!-- 右侧：解析结果 -->
      <div class="panel result-panel">
        <div class="panel-h">
          <span class="panel-title">解析结果</span>
          <div class="result-tags">
            <el-tag v-if="lastMode" :type="lastMode === 'llm' ? 'success' : 'warning'" size="small">
              {{ lastMode === 'llm' ? 'LLM 模式' : 'Mock 模式' }}
            </el-tag>
            <el-tag v-if="extracted.length" type="primary" size="small">
              {{ extracted.length }} 条
            </el-tag>
            <el-tag v-if="selectedRows.length" type="info" size="small">
              已选 {{ selectedRows.length }}
            </el-tag>
          </div>
        </div>

        <div class="panel-body result-body">
          <el-empty
            v-if="!extracting && !extracted.length"
            description="上传文档后点击「AI 解析需求点」"
            :image-size="72"
          />

          <div v-if="extracting" class="stream-progress">
            <el-progress :percentage="progressPercent" :stroke-width="8" striped striped-flow />
            <p class="progress-text">{{ progressMessage }}</p>
            <p v-if="extracted.length" class="saved-tip">
              已提取 {{ extracted.length }} 条需求点，解析完成后可编辑并导入
            </p>
          </div>

          <div v-if="extracted.length" class="table-wrap">
            <el-table
              ref="tableRef"
              :data="extracted"
              row-key="_key"
              stripe
              border
              height="100%"
              @selection-change="handleSelectionChange"
            >
              <el-table-column type="selection" width="45" fixed="left" />
              <el-table-column label="标题" min-width="160" fixed="left">
                <template #default="{ row }">
                  <el-input v-model="row.title" :maxlength="TITLE_MAX_LEN" />
                </template>
              </el-table-column>
              <el-table-column label="类型" width="120">
                <template #default="{ row }">
                  <el-select v-model="row.req_type" style="width: 100%">
                    <el-option label="功能测试" value="functional" />
                    <el-option label="接口测试" value="api" />
                    <el-option label="性能测试" value="performance" />
                    <el-option label="安全测试" value="security" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="优先级" width="90" align="center">
                <template #default="{ row }">
                  <el-select v-model="row.priority" style="width: 100%">
                    <el-option
                      v-for="p in ['P0', 'P1', 'P2', 'P3']"
                      :key="p"
                      :label="p"
                      :value="p"
                    />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="描述" min-width="240">
                <template #default="{ row }">
                  <el-input
                    v-model="row.description"
                    :maxlength="LONG_TEXT_MAX_LEN"
                    type="textarea"
                    :rows="2"
                    resize="none"
                  />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="72" fixed="right" align="center">
                <template #default="{ row }">
                  <el-popconfirm title="确认删除该需求点？" @confirm="handleRemoveRow(row)">
                    <template #reference>
                      <el-button link type="danger" size="small">删除</el-button>
                    </template>
                  </el-popconfirm>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div v-if="extracted.length && !extracting" class="result-footer">
            <el-text v-if="extractMessage" type="info" size="small">{{ extractMessage }}</el-text>
            <el-text v-else type="success" size="small">
              共解析 {{ extracted.length }} 条需求点，勾选后导入到需求点
            </el-text>
            <div class="result-actions">
              <el-button @click="toggleSelectAll">
                {{ allSelected ? '取消全选' : '全选' }}
              </el-button>
              <el-button
                type="primary"
                :loading="importing"
                :disabled="!selectedRows.length"
                @click="handleImport"
              >
                导入到需求点{{ selectedRows.length ? ` (${selectedRows.length})` : '' }}
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { LONG_TEXT_MAX_LEN, TITLE_MAX_LEN } from '@/constants/limits'
import { computed, ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, genFileId } from 'element-plus'
import type { TableInstance, UploadFile, UploadInstance, UploadRawFile } from 'element-plus'
import { projectApi, requirementApi, settingsApi } from '@/api'
import { unwrapProjectList } from '@/api/project'
import type { Schemas } from '@/api/types'
import type { Project } from '@/types/common'
import { useRequirementExtractStore, type ExtractedRow } from '@/stores/requirementExtract'
import LlmProviderLabel from '@/components/LlmProviderLabel.vue'
import { formatLlmProviderLabel } from '@/utils/llmProviderLabel'

const router = useRouter()
const extractStore = useRequirementExtractStore()
const MAX_FILE_SIZE = 50 * 1024 * 1024
const FILE_SIZE_TIP = '文件大小不超过50M'
const { extracting, extracted, lastMode, extractMessage, progressMessage, progressPercent } =
  storeToRefs(extractStore)

// scopedProjectId 传入时锁定该项目（新壳工作区）：隐藏项目下拉；不传时保持独立页原行为
const props = defineProps<{ scopedProjectId?: number }>()
const scoped = computed(() => props.scopedProjectId != null)

const projects = ref<Project[]>([])
const llmProviders = ref<Schemas['LLMProviderOptionOut'][]>([])
const projectId = ref<number | null>(props.scopedProjectId ?? null)
const providerId = ref<number | null>(null)
const providersLoading = ref(false)
const mockMode = ref(false)
const selectedFile = ref<File | null>(null)
const importing = ref(false)
const selectedRows = ref<ExtractedRow[]>([])
const tableRef = ref<TableInstance>()
const uploadRef = ref<UploadInstance>()

const allSelected = computed(
  () => extracted.value.length > 0 && selectedRows.value.length === extracted.value.length,
)

const selectedProvider = computed(
  () => llmProviders.value.find((item) => item.id === providerId.value) ?? null,
)

// 新壳切换项目 → 锁定新项目并清空上一项目的解析结果
watch(
  () => props.scopedProjectId,
  (v) => {
    if (v == null) return
    projectId.value = v
    extractStore.cancelExtract()
    extractStore.resetSession()
    selectedRows.value = []
  },
)

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

async function loadProjects() {
  projects.value = unwrapProjectList(await projectApi.list())
  if (projects.value.length && !projectId.value) {
    projectId.value = projects.value[0].id
  }
}

async function loadProviders() {
  providersLoading.value = true
  try {
    const data = await settingsApi.getLLMOptions()
    llmProviders.value = data.providers || []
    mockMode.value = data.mock_mode
    if (data.active_provider_id) {
      providerId.value = data.active_provider_id
    } else if (llmProviders.value.length) {
      providerId.value = llmProviders.value[0].id
    }
  } finally {
    providersLoading.value = false
  }
}

function resetUploadPanel() {
  selectedFile.value = null
  selectedRows.value = []
  uploadRef.value?.clearFiles()
}

function resetExtractionResult() {
  extractStore.resetSession()
  selectedRows.value = []
}

function acceptFile(raw: File | undefined): boolean {
  if (!raw) {
    selectedFile.value = null
    return false
  }
  if (raw.size > MAX_FILE_SIZE) {
    ElMessage.warning(FILE_SIZE_TIP)
    uploadRef.value?.clearFiles()
    selectedFile.value = null
    return false
  }
  selectedFile.value = raw
  resetExtractionResult()
  return true
}

function handleFileChange(uploadFile: UploadFile) {
  if (extracting.value) return
  if (!acceptFile(uploadFile.raw)) {
    uploadRef.value?.clearFiles()
  }
}

function handleExceed(files: File[]) {
  if (extracting.value || !files.length) return
  uploadRef.value?.clearFiles()
  const raw = files[0] as UploadRawFile
  raw.uid = genFileId()
  uploadRef.value?.handleStart(raw)
}

function handleFileRemove() {
  selectedFile.value = null
  resetExtractionResult()
}

function handleSelectionChange(rows: ExtractedRow[]) {
  selectedRows.value = rows
}

function handleRemoveRow(row: ExtractedRow) {
  extractStore.removeRow(row._key)
  selectedRows.value = selectedRows.value.filter((item) => item._key !== row._key)
}

function toggleSelectAll() {
  if (!tableRef.value) return
  if (allSelected.value) {
    tableRef.value.clearSelection()
  } else {
    extracted.value.forEach((row) => tableRef.value?.toggleRowSelection(row, true))
  }
}

async function handleExtract() {
  if (!projectId.value || !selectedFile.value) return
  if (selectedFile.value.size > MAX_FILE_SIZE) {
    ElMessage.warning(FILE_SIZE_TIP)
    return
  }
  if (!mockMode.value) {
    const provider = llmProviders.value.find((item) => item.id === providerId.value)
    if (provider && !provider.api_key_configured) {
      ElMessage.warning('当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式')
      return
    }
  }

  selectedRows.value = []
  await extractStore.startExtract(
    projectId.value,
    selectedFile.value,
    providerId.value ?? undefined,
  )
}

async function syncSelectAllExtracted() {
  await nextTick()
  const table = tableRef.value
  if (!table || !extracted.value.length) return
  extracted.value.forEach((row) => table.toggleRowSelection(row, true))
}

// 流式写入时自动勾选全部行（表格随数据增长重渲染会丢选中态，需反复全选）
watch(
  () => extracted.value.length,
  async (len, prev) => {
    if (len <= (prev ?? 0)) return
    await syncSelectAllExtracted()
  },
)

watch(extracting, async (isExtracting, wasExtracting) => {
  if (wasExtracting && !isExtracting && extracted.value.length) {
    await syncSelectAllExtracted()
  }
})

async function handleImport() {
  if (!selectedRows.value.length) return
  await ElMessageBox.confirm(
    `确认将选中的 ${selectedRows.value.length} 条需求导入到需求点？`,
    '导入确认',
    { type: 'info' },
  )

  importing.value = true
  try {
    const res = await requirementApi.batchImport({
      project_id: projectId.value!,
      requirements: selectedRows.value.map((item) => ({
        title: item.title,
        description: item.description,
        req_type: item.req_type,
        priority: item.priority,
      })),
    })
    ElMessage.success(res.message || '导入成功')
    await router.push({
      path: `/hub/workspace/${projectId.value}`,
      hash: '#domain=requirements&section=req-points',
    })
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  extractStore.onEnterPage()
  if (!extracting.value) {
    resetUploadPanel()
  }
  await Promise.all([loadProjects(), loadProviders()])
})

onUnmounted(() => {
  extractStore.onLeavePage()
  if (!extracting.value) {
    resetUploadPanel()
  }
})
</script>

<style scoped>
.requirement-docs {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.docs-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(320px, 2fr) minmax(0, 3fr);
  gap: var(--ax-gap-sm);
}

.panel {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.panel-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-gap);
  padding: var(--ax-space-2-5) var(--ax-space-3-5);
  border-bottom: 1px solid var(--ax-border);
  flex: none;
}

.panel-title {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  font-size: var(--ax-text-body-size);
  font-weight: 600;
  color: var(--ax-text);
}

.panel-title .el-icon {
  color: var(--ax-brand);
}

.panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--ax-space-3-5) var(--ax-space-4);
}

.config-panel .panel-body {
  display: flex;
  flex-direction: column;
  gap: var(--ax-gap-sm);
}

.docs-form :deep(.el-form-item) {
  margin-bottom: var(--ax-space-3-5);
}

.docs-form :deep(.el-form-item__label) {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.docs-upload :deep(.el-upload-dragger) {
  padding: var(--ax-space-5) var(--ax-space-3);
  border-radius: var(--ax-radius);
  border-color: var(--ax-border);
  background: var(--ax-bg-subtle);
  transition:
    border-color var(--ax-transition),
    background var(--ax-transition);
}

.docs-upload :deep(.el-upload-dragger:hover) {
  border-color: var(--ax-brand);
  background: var(--ax-brand-subtle);
}

.upload-icon {
  font-size: 40px;
  color: var(--ax-text-placeholder);
  margin-bottom: var(--ax-space-1-5);
}

.upload-tip {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-caption-size);
  text-align: center;
}

.file-chip {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  margin-top: var(--ax-space-2);
  padding: var(--ax-space-2) var(--ax-space-2-5);
  border-radius: var(--ax-radius);
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
}

.file-chip-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text);
}

.extract-btn {
  width: 100%;
}

.mode-alert {
  flex: none;
  margin-top: auto;
}

.result-tags {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  flex-wrap: wrap;
}

.result-body {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.result-body :deep(.el-empty) {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.table-wrap {
  flex: 1;
  min-height: 0;
}

.table-wrap :deep(.el-table) {
  font-size: var(--ax-text-body-sm-size);
}

.table-wrap :deep(.el-textarea__inner) {
  font-size: var(--ax-text-body-sm-size);
}

.stream-progress {
  flex: none;
  margin-bottom: var(--ax-gap-sm);
}

.progress-text {
  margin: var(--ax-space-2) 0 0;
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-body-sm-size);
}

.saved-tip {
  margin: var(--ax-space-1-5) 0 0;
  color: var(--ax-success);
  font-size: var(--ax-text-body-sm-size);
}

.result-footer {
  flex: none;
  margin-top: var(--ax-gap-sm);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-gap);
  padding-top: var(--ax-space-2-5);
  border-top: 1px solid var(--ax-border);
}

.result-actions {
  display: flex;
  gap: var(--ax-space-2);
  flex-shrink: 0;
}

.form-tip {
  margin-top: var(--ax-space-1);
  color: var(--ax-text-tertiary);
  font-size: var(--ax-text-caption-size);
}

@media (max-width: 960px) {
  .requirement-docs {
    overflow: auto;
  }

  .docs-grid {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }
}
</style>

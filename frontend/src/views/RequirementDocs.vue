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
                <el-option
                  v-for="item in llmProviders"
                  :key="item.id"
                  :label="formatProviderLabel(item)"
                  :value="item.id"
                />
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
                :disabled="scopedTaskActive"
                accept=".txt,.md,.docx,text/plain,text/markdown"
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
                :loading="scopedTaskActive"
                :disabled="!projectId || !selectedFile || (restoringRunning && storeMatchesProject)"
                @click="handleExtract"
              >
                <el-icon><MagicStick /></el-icon>
                {{ scopedTaskActive ? '正在解析，请稍候...' : 'AI 解析需求点' }}
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
            <el-tag
              v-if="scopedLastMode && scopedExtracted.length"
              :type="scopedLastMode === 'llm' ? 'success' : 'warning'"
              size="small"
            >
              {{ scopedLastMode === 'llm' ? 'LLM 模式' : 'Mock 模式' }}
            </el-tag>
            <el-tag v-if="scopedExtracted.length" type="primary" size="small">
              {{ scopedExtracted.length }} 条
            </el-tag>
          </div>
        </div>

        <div class="panel-body result-body">
          <el-empty
            v-if="!scopedHasResultsPanel"
            description="上传文档后点击「AI 解析需求点」；进行中的任务可在 AI 需求任务查看进度"
            :image-size="72"
          />

          <template v-if="scopedHasResultsPanel">
            <div v-if="scopedTaskActive" class="stream-progress">
              <el-progress
                :percentage="scopedProgressPercent"
                :stroke-width="8"
                striped
                striped-flow
              />
              <p class="progress-text">{{ scopedProgressMessage }}</p>
              <p v-if="scopedExtracted.length" class="saved-tip">
                已实时写入需求点 {{ scopedExtracted.length }} 条
                <el-button type="primary" link @click="goToRequirementPoints"
                  >前往需求点查看</el-button
                >
              </p>
            </div>

            <div
              v-if="scopedExtracted.length && !scopedTaskActive && scopedActiveTarget"
              class="restore-hint-bar"
            >
              <el-text size="small" type="info">文档：{{ scopedActiveTarget }}</el-text>
              <el-button type="primary" link @click="goToRequirementPoints"
                >前往需求点查看</el-button
              >
            </div>

            <div v-if="scopedExtracted.length" class="table-wrap">
              <el-table :data="pagedExtracted" row-key="_key" stripe border height="100%">
                <el-table-column label="标题" min-width="160" fixed="left">
                  <template #default="{ row }">
                    <el-input
                      v-model="row.title"
                      :maxlength="REQ_CASE_TITLE_MAX_LEN"
                      show-word-limit
                    />
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
                    <el-input v-model="row.description" type="textarea" :rows="2" resize="none" />
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <div v-if="scopedExtracted.length" class="result-pagination">
              <el-pagination
                v-model:current-page="resultPage"
                v-model:page-size="resultPageSize"
                :total="scopedExtracted.length"
                :page-sizes="[...PAGE_SIZE_OPTIONS]"
                layout="total, sizes, prev, pager, next, jumper"
                small
                background
                @size-change="handleResultPageSizeChange"
              />
            </div>

            <div v-if="scopedExtracted.length && !scopedTaskActive" class="result-footer">
              <el-text v-if="scopedExtractMessage" type="success" size="small">{{
                scopedExtractMessage
              }}</el-text>
              <el-button type="primary" link @click="goToRequirementPoints">
                前往需求点查看
              </el-button>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { ElMessage, genFileId } from 'element-plus'
import type { UploadFile, UploadInstance, UploadRawFile } from 'element-plus'
import { projectApi, settingsApi } from '@/api'
import { unwrapProjectList } from '@/api/project'
import type { Schemas } from '@/api/types'
import type { Project } from '@/types/common'
import { useRequirementExtractStore } from '@/stores/requirementExtract'
import { DEFAULT_PAGE_SIZE, PAGE_SIZE_OPTIONS } from '@/constants/pagination'
import { REQ_CASE_TITLE_MAX_LEN } from '@/constants/limits'

const router = useRouter()
const extractStore = useRequirementExtractStore()
const ALLOWED_EXTENSIONS = ['.txt', '.md', '.docx']
const MAX_FILE_SIZE = 50 * 1024 * 1024
const FILE_SIZE_TIP = '文件大小不超过 50M'
const FILE_TYPE_TIP = '仅支持 .txt / .md / .docx 格式'
const {
  restoringRunning,
  taskActive,
  hasResultsPanel,
  extracted,
  lastMode,
  extractMessage,
  progressMessage,
  progressPercent,
  activeTarget,
} = storeToRefs(extractStore)

// scopedProjectId 传入时锁定该项目（新壳工作区）：隐藏项目下拉；不传时保持独立页原行为
const props = defineProps<{ scopedProjectId?: number; embedded?: boolean }>()
const scoped = computed(() => props.scopedProjectId != null)

const projects = ref<Project[]>([])
const llmProviders = ref<Schemas['LLMProviderOptionOut'][]>([])
const projectId = ref<number | null>(props.scopedProjectId ?? null)
const providerId = ref<number | null>(null)
const providersLoading = ref(false)
const mockMode = ref(false)
const selectedFile = ref<File | null>(null)
const uploadRef = ref<UploadInstance>()
const resultPage = ref(1)
const resultPageSize = ref(DEFAULT_PAGE_SIZE)

/** 全局 Pinia 与当前页项目一致时才展示/操作解析结果（跨项目切换隔离） */
const storeMatchesProject = computed(
  () => projectId.value != null && extractStore.activeProjectId === projectId.value,
)
const scopedExtracted = computed(() => (storeMatchesProject.value ? extracted.value : []))
const scopedTaskActive = computed(() => storeMatchesProject.value && taskActive.value)
const scopedHasResultsPanel = computed(() => storeMatchesProject.value && hasResultsPanel.value)
const scopedProgressMessage = computed(() =>
  storeMatchesProject.value ? progressMessage.value : '',
)
const scopedProgressPercent = computed(() =>
  storeMatchesProject.value ? progressPercent.value : 0,
)
const scopedLastMode = computed(() => (storeMatchesProject.value ? lastMode.value : ''))
const scopedActiveTarget = computed(() => (storeMatchesProject.value ? activeTarget.value : ''))
const scopedExtractMessage = computed(() => (storeMatchesProject.value ? extractMessage.value : ''))

const pagedExtracted = computed(() => {
  const start = (resultPage.value - 1) * resultPageSize.value
  return scopedExtracted.value.slice(start, start + resultPageSize.value)
})

watch(scopedTaskActive, (active, wasActive) => {
  if (wasActive && !active) {
    selectedFile.value = null
    uploadRef.value?.clearFiles()
    resultPage.value = 1
  }
})

watch(
  () => scopedExtracted.value.length,
  (len) => {
    const maxPage = Math.max(1, Math.ceil(len / resultPageSize.value) || 1)
    if (resultPage.value > maxPage) {
      resultPage.value = maxPage
    }
  },
)

function handleResultPageSizeChange() {
  resultPage.value = 1
}

// 新壳切换项目 → 锁定新项目并清空上一项目的解析结果
watch(
  () => props.scopedProjectId,
  (v, old) => {
    if (v == null) return
    projectId.value = v
    if (old != null && old !== v) {
      extractStore.cancelExtract()
    }
    extractStore.onEnterRequirementDocsPage(v)
  },
  { immediate: true },
)

function formatProviderLabel(item: Schemas['LLMProviderOptionOut']) {
  const tags = []
  if (item.is_default) tags.push('默认')
  if (!item.api_key_configured) tags.push('未配置Key')
  const suffix = tags.length ? ` (${tags.join(' / ')})` : ''
  return `${item.name}${suffix}`
}

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

function resetExtractionResult() {
  extractStore.resetSession()
  resultPage.value = 1
}

function getFileExtension(name: string): string {
  const dotIndex = name.lastIndexOf('.')
  if (dotIndex === -1) return ''
  return name.slice(dotIndex).toLowerCase()
}

function acceptFile(raw: File | undefined): boolean {
  if (!raw) {
    selectedFile.value = null
    return false
  }
  const ext = getFileExtension(raw.name)
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    ElMessage.warning(FILE_TYPE_TIP)
    uploadRef.value?.clearFiles()
    selectedFile.value = null
    return false
  }
  if (raw.size >= MAX_FILE_SIZE) {
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
  if (scopedTaskActive.value) return
  if (!acceptFile(uploadFile.raw)) {
    uploadRef.value?.clearFiles()
  }
}

function handleExceed(files: File[]) {
  if (scopedTaskActive.value || !files.length) return
  uploadRef.value?.clearFiles()
  const raw = files[0] as UploadRawFile
  if (!acceptFile(raw)) return
  raw.uid = genFileId()
  uploadRef.value?.handleStart(raw)
}

function handleFileRemove() {
  selectedFile.value = null
  resetExtractionResult()
}

function goToRequirementPoints() {
  if (projectId.value == null) {
    ElMessage.warning('请先选择项目')
    return
  }
  void router.push({
    name: 'WorkspaceRequirementPoints',
    params: { projectId: projectId.value },
  })
}

async function handleExtract() {
  if (!projectId.value || !selectedFile.value) return
  if (!ALLOWED_EXTENSIONS.includes(getFileExtension(selectedFile.value.name))) {
    ElMessage.warning(FILE_TYPE_TIP)
    return
  }
  if (selectedFile.value.size >= MAX_FILE_SIZE) {
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

  await extractStore.startExtract(
    projectId.value,
    selectedFile.value,
    providerId.value ?? undefined,
  )
}

watch(projectId, (id, prev) => {
  if (id == null || prev == null || prev === id) return
  extractStore.cancelExtract()
  extractStore.onEnterRequirementDocsPage(id)
})

onMounted(async () => {
  await Promise.all([loadProjects(), loadProviders()])
  if (projectId.value != null && props.scopedProjectId == null) {
    extractStore.onEnterRequirementDocsPage(projectId.value)
  }
})

onUnmounted(() => {
  extractStore.onLeaveRequirementDocsPage()
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
  padding: 10px 14px;
  border-bottom: 1px solid var(--ax-border);
  flex: none;
}

.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--ax-font);
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
  padding: 14px 16px;
}

.config-panel .panel-body {
  display: flex;
  flex-direction: column;
  gap: var(--ax-gap-sm);
}

.docs-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.docs-form :deep(.el-form-item__label) {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.docs-upload :deep(.el-upload-dragger) {
  padding: 20px 12px;
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
  margin-bottom: 6px;
}

.upload-tip {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
  text-align: center;
}

.file-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 8px 10px;
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
  font-size: var(--ax-font-sm);
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
  gap: 6px;
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
  font-size: var(--ax-font-sm);
}

.table-wrap :deep(.el-textarea__inner) {
  font-size: var(--ax-font-sm);
}

.restore-hint-bar {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-gap);
  margin-bottom: var(--ax-gap-sm);
  padding: 6px 10px;
  border-radius: var(--ax-radius);
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
}

.stream-progress {
  flex: none;
  margin-bottom: var(--ax-gap-sm);
}

.restore-hint {
  flex: none;
  margin-bottom: var(--ax-gap-sm);
}

.progress-text {
  margin: 8px 0 0;
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-sm);
}

.saved-tip {
  margin: 6px 0 0;
  color: var(--ax-success);
  font-size: var(--ax-font-sm);
}

.result-footer {
  flex: none;
  margin-top: var(--ax-gap-sm);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-gap);
  padding-top: 10px;
  border-top: 1px solid var(--ax-border);
}

.result-pagination {
  flex: none;
  display: flex;
  justify-content: flex-end;
  margin-top: var(--ax-gap-sm);
  padding-top: 8px;
}

.result-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.form-tip {
  margin-top: 4px;
  color: var(--ax-text-tertiary);
  font-size: var(--ax-font-xs);
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

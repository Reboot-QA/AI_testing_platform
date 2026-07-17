<template>
  <div>
    <el-card class="upload-card">
      <template #header>
        <span>上传需求文档</span>
      </template>

      <el-form label-width="90px">
        <el-form-item label="项目">
          <el-select v-model="projectId" filterable placeholder="选择项目" style="width: 280px">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="大模型">
          <el-select
            v-model="providerId"
            placeholder="请选择大模型"
            style="width: 280px"
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
        </el-form-item>
        <el-form-item label="文档文件">
          <el-upload
            drag
            :auto-upload="false"
            :limit="1"
            accept=".txt,.md,.docx"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
            <template #tip>
              <div class="upload-tip">支持 .txt / .md / .docx，最大 50MB</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
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
        :title="
          mockMode
            ? '当前为 Mock 模式，将使用本地规则提取需求点'
            : '未配置 API Key 的模型无法解析，请先在系统管理中配置 Key 或开启 Mock 模式'
        "
        type="info"
        :closable="false"
        show-icon
      />
    </el-card>

    <el-card v-if="extracting || extracted.length" class="result-card">
      <template #header>
        <div class="result-header">
          <div>
            <span>解析结果</span>
            <el-tag
              v-if="lastMode"
              :type="lastMode === 'llm' ? 'success' : 'warning'"
              size="small"
              class="mode-tag"
            >
              {{ lastMode === 'llm' ? 'LLM 模式' : 'Mock 模式' }}
            </el-tag>
            <el-text v-if="extractMessage" type="info" size="small">{{ extractMessage }}</el-text>
          </div>
          <div v-if="!extracting" class="result-actions">
            <el-button @click="toggleSelectAll">{{ allSelected ? '取消全选' : '全选' }}</el-button>
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
      </template>

      <div v-if="extracting" class="stream-progress">
        <el-progress :percentage="progressPercent" :stroke-width="10" />
        <p class="progress-text">{{ progressMessage }}</p>
      </div>

      <el-table
        v-if="extracted.length"
        ref="tableRef"
        :data="extracted"
        row-key="_key"
        stripe
        border
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="45" />
        <el-table-column label="标题" min-width="180">
          <template #default="{ row }">
            <el-input v-model="row.title" />
          </template>
        </el-table-column>
        <el-table-column label="类型" width="130">
          <template #default="{ row }">
            <el-select v-model="row.req_type" style="width: 100%">
              <el-option label="功能测试" value="functional" />
              <el-option label="接口测试" value="api" />
              <el-option label="性能测试" value="performance" />
              <el-option label="安全测试" value="security" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="优先级" width="100">
          <template #default="{ row }">
            <el-select v-model="row.priority" style="width: 100%">
              <el-option v-for="p in ['P0', 'P1', 'P2', 'P3']" :key="p" :label="p" :value="p" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="描述" min-width="280">
          <template #default="{ row }">
            <el-input v-model="row.description" type="textarea" :rows="2" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-popconfirm title="确认删除该需求点？" @confirm="handleRemoveRow(row)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { TableInstance, UploadFile } from 'element-plus'
import { projectApi, requirementApi, settingsApi } from '@/api'
import { unwrapProjectList } from '@/api/project'
import type { Schemas } from '@/api/types'
import type { Project } from '@/types/common'

type ExtractedRequirement = Schemas['ExtractedRequirement']

interface ExtractedRow extends ExtractedRequirement {
  _key: number
}

interface ExtractStreamEvent {
  type: string
  message?: string
  current?: number
  chunk?: number
  chunk_total?: number
  mode?: string
  total?: number
  data?: ExtractedRequirement
}

const router = useRouter()
const projects = ref<Project[]>([])
const llmProviders = ref<Schemas['LLMProviderOptionOut'][]>([])
const projectId = ref<number | null>(null)
const providerId = ref<number | null>(null)
const providersLoading = ref(false)
const mockMode = ref(false)
const selectedFile = ref<File | null>(null)
const extracting = ref(false)
const importing = ref(false)
const extracted = ref<ExtractedRow[]>([])
const selectedRows = ref<ExtractedRow[]>([])
const lastMode = ref('')
const extractMessage = ref('')
const tableRef = ref<TableInstance>()
const progressMessage = ref('')
const progressCurrent = ref(0)
const progressChunk = ref(0)
const progressChunkTotal = ref(0)
let tempKey = 0

const allSelected = computed(
  () => extracted.value.length > 0 && selectedRows.value.length === extracted.value.length,
)

const progressPercent = computed(() => {
  if (progressChunkTotal.value) {
    const chunkProgress = progressChunk.value / progressChunkTotal.value
    return Math.min(99, Math.round(chunkProgress * 100))
  }
  if (extracting.value) return Math.min(95, 10 + progressCurrent.value * 5)
  return 100
})

function formatProviderLabel(item: Schemas['LLMProviderOptionOut']) {
  const tags = []
  if (item.is_default) tags.push('默认')
  if (!item.api_key_configured) tags.push('未配置Key')
  const suffix = tags.length ? ` (${tags.join(' / ')})` : ''
  return `${item.name}${suffix}`
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

function handleFileChange(uploadFile: UploadFile) {
  selectedFile.value = uploadFile.raw ?? null
}

function handleFileRemove() {
  selectedFile.value = null
}

function handleSelectionChange(rows: ExtractedRow[]) {
  selectedRows.value = rows
}

function handleRemoveRow(row: ExtractedRow) {
  extracted.value = extracted.value.filter((item) => item._key !== row._key)
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
  if (!mockMode.value) {
    const provider = llmProviders.value.find((item) => item.id === providerId.value)
    if (provider && !provider.api_key_configured) {
      ElMessage.warning('当前模型未配置 API Key，请前往系统管理配置，或开启 Mock 模式')
      return
    }
  }

  extracting.value = true
  extracted.value = []
  selectedRows.value = []
  lastMode.value = ''
  extractMessage.value = ''
  progressMessage.value = '准备分析...'
  progressCurrent.value = 0
  progressChunk.value = 0
  progressChunkTotal.value = 0
  tempKey = 0

  try {
    await requirementApi.extractFromDocumentStream(
      projectId.value,
      selectedFile.value,
      providerId.value ?? undefined,
      async (event: ExtractStreamEvent) => {
        if (event.type === 'status') {
          progressMessage.value = event.message || ''
          progressCurrent.value = event.current ?? progressCurrent.value
          progressChunk.value = event.chunk ?? progressChunk.value
          progressChunkTotal.value = event.chunk_total ?? progressChunkTotal.value
        } else if (event.type === 'requirement' && event.data) {
          const row: ExtractedRow = { ...event.data, _key: ++tempKey }
          extracted.value.push(row)
          progressCurrent.value = event.current ?? progressCurrent.value
          progressChunk.value = event.chunk ?? progressChunk.value
          progressChunkTotal.value = event.chunk_total ?? progressChunkTotal.value
          progressMessage.value = `已提取 ${event.current} 条需求点...`
          await nextTick()
          tableRef.value?.toggleRowSelection(row, true)
        } else if (event.type === 'done') {
          lastMode.value = event.mode || ''
          progressCurrent.value = event.total ?? progressCurrent.value
          progressChunk.value = progressChunkTotal.value || progressChunk.value
          progressMessage.value = event.message || ''
          extractMessage.value = event.message || ''
          ElMessage.success(event.message || '解析完成')
        } else if (event.type === 'error') {
          throw new Error(event.message)
        }
      },
    )
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : '解析失败'
    ElMessage.error(message)
  } finally {
    extracting.value = false
  }
}

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
    router.push('/requirements')
  } finally {
    importing.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadProjects(), loadProviders()])
})
</script>

<style scoped>
.upload-card {
  margin-bottom: 20px;
}

.upload-icon {
  font-size: 48px;
  color: #909399;
  margin-bottom: 8px;
}

.upload-tip {
  color: #909399;
  font-size: 13px;
}

.result-card {
  margin-top: 4px;
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.mode-tag {
  margin-left: 8px;
}

.result-actions {
  display: flex;
  gap: 8px;
}

.stream-progress {
  margin-bottom: 16px;
}

.progress-text {
  margin: 10px 0 0;
  color: #606266;
  font-size: 13px;
}
</style>

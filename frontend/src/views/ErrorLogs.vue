<template>
  <div class="error-logs">
    <el-row :gutter="16" class="stats-row">
      <el-col v-for="item in categories" :key="item.key" :xs="24" :sm="8">
        <el-card
          shadow="never"
          class="stat-card"
          :class="{ active: activeCategory === item.key }"
          @click="switchCategory(item.key)"
        >
          <div class="stat-body">
            <div class="stat-title">{{ item.label }}</div>
            <div class="stat-content">
              <div class="stat-meta">
                <el-tag :type="item.exists ? 'success' : 'info'" size="small">
                  {{ item.exists ? '已启用' : '暂无文件' }}
                </el-tag>
                <span>{{ formatSize(item.size) }}</span>
                <span>{{ item.line_count || 0 }} 行</span>
              </div>
            </div>
            <div class="stat-path">{{ item.filename }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never" class="stat-card summary-card">
          <div class="stat-body">
            <div class="stat-title">错误总数</div>
            <div class="stat-content">
              <div class="summary-value">{{ totalMatched }}</div>
            </div>
            <div class="stat-path">目录: {{ logDir || '-' }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="viewer-card">
      <template #header>
        <div class="toolbar">
          <div class="toolbar-left">
            <el-segmented
              v-model="activeCategory"
              :options="categoryOptions"
              @change="handleCategoryChange"
            />
            <el-select
              v-if="activeCategory !== 'application'"
              v-model="statusMin"
              clearable
              placeholder="状态码"
              style="width: 120px"
              @change="resetPageAndRefresh"
            >
              <el-option label="≥ 400" :value="400" />
              <el-option label="≥ 401" :value="401" />
              <el-option label="≥ 403" :value="403" />
              <el-option label="≥ 404" :value="404" />
              <el-option label="≥ 500" :value="500" />
            </el-select>
            <el-select
              v-if="activeCategory !== 'application'"
              v-model="methodFilter"
              clearable
              placeholder="方法"
              style="width: 110px"
              @change="resetPageAndRefresh"
            >
              <el-option label="GET" value="GET" />
              <el-option label="POST" value="POST" />
              <el-option label="PUT" value="PUT" />
              <el-option label="DELETE" value="DELETE" />
              <el-option label="PATCH" value="PATCH" />
            </el-select>
            <el-input
              v-model="keyword"
              :maxlength="SEARCH_MAX_LEN"
              clearable
              placeholder="搜索路径/消息"
              style="width: 220px"
              @keyup.enter="resetPageAndRefresh"
              @clear="resetPageAndRefresh"
            />
          </div>
          <div class="toolbar-right">
            <el-switch
              v-model="liveMode"
              active-text="实时"
              inactive-text="静态"
              @change="handleLiveToggle"
            />
            <el-button :loading="loading" @click="refreshErrors">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <div class="log-meta">
        <span>匹配: {{ totalMatched }} 条</span>
        <span v-if="liveMode" class="live-dot">实时监听中</span>
      </div>

      <el-table
        v-loading="loading"
        :data="displayItems"
        stripe
        height="100%"
        class="error-table"
        empty-text="暂无错误日志"
      >
        <el-table-column prop="timestamp" label="时间" width="180" show-overflow-tooltip />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.category === 'api' ? 'warning' : 'danger'" size="small">
              {{ row.category === 'api' ? '接口' : '应用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="级别" width="90">
          <template #default="{ row }">
            <span :class="`level-${(row.level || 'ERROR').toLowerCase()}`">{{
              row.level || 'ERROR'
            }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="method" label="方法" width="90">
          <template #default="{ row }">
            {{ row.method || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.path || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <span v-if="row.status" :class="statusClass(row.status)">{{ row.status }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="client_ip" label="客户端" width="130" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.client_ip || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" min-width="260" show-overflow-tooltip />
      </el-table>

      <div v-if="!liveMode" class="pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          background
          layout="total, prev, pager, next"
          :page-size="pageSize"
          :total="totalMatched"
          @current-change="refreshErrors"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { errorLogsApi } from '@/api'

type ErrorCategory = 'all' | 'application' | 'api'

interface ErrorLogCategory {
  key: string
  label: string
  exists: boolean
  size: number
  line_count: number
  filename: string
}

interface ErrorLogItem {
  timestamp?: string
  category?: string
  level?: string
  method?: string
  path?: string
  status?: number
  client_ip?: string
  message?: string
  type?: string
}

const categories = ref<ErrorLogCategory[]>([])
const logDir = ref('')
const activeCategory = ref<ErrorCategory>('all')
const pageSize = 20
const currentPage = ref(1)
const keyword = ref('')
const statusMin = ref(400)
const methodFilter = ref('')
const loading = ref(false)
const liveMode = ref(true)
const displayItems = ref<ErrorLogItem[]>([])
const totalMatched = ref(0)

let streamAbort: AbortController | null = null
let refreshTimer: number | null = null

const categoryOptions = [
  { label: '全部', value: 'all' },
  { label: '应用错误', value: 'application' },
  { label: '接口错误', value: 'api' },
]

function formatSize(size: number) {
  if (!size) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function statusClass(status: number) {
  if (status >= 500) return 'status-5xx'
  if (status >= 400) return 'status-4xx'
  return ''
}

async function loadSummary() {
  const data = await errorLogsApi.summary()
  categories.value = data.categories || []
  logDir.value = data.log_dir || ''
}

async function refreshErrors() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      category: activeCategory.value,
      page: currentPage.value,
      page_size: pageSize,
      keyword: keyword.value || undefined,
    }
    if (activeCategory.value !== 'application' && statusMin.value) {
      params.status_min = statusMin.value
    }
    if (activeCategory.value !== 'application' && methodFilter.value) {
      params.method = methodFilter.value
    }
    const data = await errorLogsApi.tail(params)
    totalMatched.value = data.total_matched || 0
    const maxPage = Math.max(1, Math.ceil(totalMatched.value / pageSize))
    if (currentPage.value > maxPage) {
      currentPage.value = maxPage
      if (maxPage !== params.page) {
        await refreshErrors()
        return
      }
    }
    displayItems.value = data.items || []
  } finally {
    loading.value = false
  }
}

function resetPageAndRefresh() {
  currentPage.value = 1
  refreshErrors()
}

function stopStream() {
  if (streamAbort) {
    streamAbort.abort()
    streamAbort = null
  }
}

async function startStream() {
  stopStream()
  await refreshErrors()
  streamAbort = new AbortController()
  const token = localStorage.getItem('token')
  const params = new URLSearchParams({ category: activeCategory.value })
  try {
    const response = await fetch(`/api/v1/logs/errors/stream?${params.toString()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal: streamAbort.signal,
    })
    if (!response.ok) {
      throw new Error('实时错误日志连接失败')
    }
    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const chunks = buffer.split('\n\n')
      buffer = chunks.pop() || ''
      for (const chunk of chunks) {
        const line = chunk.trim()
        if (!line.startsWith('data:')) continue
        const payload = JSON.parse(line.slice(5).trim()) as ErrorLogItem & { type?: string }
        if (payload.type === 'item') {
          displayItems.value.unshift(payload)
          if (displayItems.value.length > pageSize) {
            displayItems.value.splice(pageSize)
          }
          totalMatched.value += 1
        }
      }
    }
  } catch (error: unknown) {
    if (error instanceof Error && error.name !== 'AbortError') {
      ElMessage.warning(error.message || '实时错误日志连接中断')
    }
  }
}

function handleLiveToggle(enabled: boolean) {
  if (enabled) {
    startStream()
  } else {
    stopStream()
    refreshErrors()
  }
}

function switchCategory(category: string) {
  if (activeCategory.value === category) return
  activeCategory.value = category as ErrorCategory
  handleCategoryChange()
}

function handleCategoryChange() {
  stopStream()
  displayItems.value = []
  currentPage.value = 1
  if (liveMode.value) {
    startStream()
  } else {
    refreshErrors()
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await loadSummary()
    if (liveMode.value) {
      await startStream()
    } else {
      await refreshErrors()
    }
    refreshTimer = window.setInterval(loadSummary, 15000)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  stopStream()
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.error-logs {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--ax-section-gap);
}

/* 顶部统计卡固定，日志卡吃掉剩余高度、内部滚动 */
.stats-row {
  flex: none;
  align-items: stretch;
}

.stats-row :deep(.el-col) {
  display: flex;
}

.viewer-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.viewer-card :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.stat-card {
  width: 100%;
  cursor: pointer;
  transition:
    border-color 0.2s,
    box-shadow 0.2s;
}

.stat-card :deep(.el-card__body) {
  height: 100%;
  padding: var(--ax-space-4) var(--ax-card-padding);
}

.stat-body {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}

.stat-card.active {
  border-color: #409eff;
  box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.15);
}

.summary-card {
  cursor: default;
}

.stat-title {
  font-size: var(--ax-text-title-sm-size);
  font-weight: 600;
  line-height: var(--ax-leading-compact);
}

.stat-content {
  flex: 1;
  min-height: 32px;
  display: flex;
  align-items: center;
}

.summary-value {
  font-size: var(--ax-text-heading-size);
  font-weight: 700;
  line-height: var(--ax-leading-tight);
  color: #f56c6c;
}

.stat-meta {
  display: flex;
  gap: var(--ax-space-3);
  align-items: center;
  flex-wrap: wrap;
  color: #606266;
  font-size: var(--ax-text-body-sm-size);
}

.stat-path {
  margin-top: auto;
  color: #909399;
  font-size: var(--ax-text-caption-size);
  line-height: var(--ax-text-caption-line);
  word-break: break-all;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: var(--ax-toolbar-gap);
  flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  gap: var(--ax-space-2-5);
  align-items: center;
  flex-wrap: wrap;
}

.log-meta {
  display: flex;
  gap: var(--ax-space-4);
  color: #909399;
  font-size: var(--ax-text-caption-size);
  margin-bottom: var(--ax-space-3);
  flex: none;
}

.live-dot {
  color: #67c23a;
}

.live-dot::before {
  content: '●';
  margin-right: var(--ax-space-1);
}

.level-error {
  color: #f56c6c;
  font-weight: 600;
}

.level-warn {
  color: #e6a23c;
  font-weight: 600;
}

.status-4xx {
  color: #e6a23c;
  font-weight: 600;
}

.status-5xx {
  color: #f56c6c;
  font-weight: 600;
}

.error-table {
  width: 100%;
  flex: 1;
  min-height: 0;
}

.pagination-bar {
  flex: none;
  display: flex;
  justify-content: flex-end;
  margin-top: var(--ax-space-3);
}
</style>

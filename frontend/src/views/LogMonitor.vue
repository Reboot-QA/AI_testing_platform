<template>
  <div class="log-monitor">
    <el-tabs v-model="activeTab" class="monitor-tabs">
      <el-tab-pane label="内置监控" name="builtin">
        <el-row :gutter="16" class="stats-row">
      <el-col v-for="item in sources" :key="item.key" :xs="24" :sm="8">
        <el-card shadow="never" class="stat-card" :class="{ active: activeSource === item.key }" @click="switchSource(item.key)">
          <div class="stat-title">{{ item.label }}</div>
          <div class="stat-meta">
            <el-tag :type="item.exists ? 'success' : 'info'" size="small">
              {{ item.exists ? '在线' : '暂无文件' }}
            </el-tag>
            <span>{{ formatSize(item.size) }}</span>
            <span>{{ item.line_count || 0 }} 行</span>
          </div>
          <div class="stat-path">{{ item.filename }}</div>
          <div v-if="item.modified_at" class="stat-time">更新: {{ formatTime(item.modified_at) }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="viewer-card">
      <template #header>
        <div class="toolbar">
          <div class="toolbar-left">
            <el-segmented v-model="activeSource" :options="sourceOptions" @change="handleSourceChange" />
            <el-select v-model="lineCount" style="width: 110px" @change="refreshLogs">
              <el-option label="100 行" :value="100" />
              <el-option label="200 行" :value="200" />
              <el-option label="500 行" :value="500" />
              <el-option label="1000 行" :value="1000" />
            </el-select>
            <el-select v-model="levelFilter" clearable placeholder="级别" style="width: 110px" @change="refreshLogs">
              <el-option label="ERROR" value="ERROR" />
              <el-option label="WARN" value="WARN" />
              <el-option label="INFO" value="INFO" />
              <el-option label="DEBUG" value="DEBUG" />
            </el-select>
            <el-input
              v-model="keyword"
              clearable
              placeholder="搜索关键字"
              style="width: 220px"
              @keyup.enter="refreshLogs"
              @clear="refreshLogs"
            />
          </div>
          <div class="toolbar-right">
            <el-switch v-model="liveMode" active-text="实时" inactive-text="静态" @change="handleLiveToggle" />
            <el-switch v-model="autoScroll" active-text="自动滚动" inactive-text="暂停滚动" />
            <el-button :loading="loading" @click="refreshLogs">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button @click="downloadLog">
              <el-icon><Download /></el-icon>
              下载
            </el-button>
          </div>
        </div>
      </template>

      <div class="log-meta">
        <span>目录: {{ logDir || '-' }}</span>
        <span>匹配: {{ totalMatched }} 行</span>
        <span v-if="liveMode" class="live-dot">实时监听中</span>
      </div>

      <div ref="logContainerRef" v-loading="loading" class="log-viewer">
        <div v-if="!displayLines.length && !loading" class="empty-tip">暂无日志内容</div>
        <div
          v-for="(line, index) in displayLines"
          :key="`${line.no || 'live'}-${index}-${line.text}`"
          class="log-line"
          :class="`level-${(line.level || 'INFO').toLowerCase()}`"
        >
          <span class="line-no">{{ line.no ?? '·' }}</span>
          <span class="line-level">{{ line.level || 'INFO' }}</span>
          <span class="line-text">{{ line.text }}</span>
        </div>
      </div>
    </el-card>
      </el-tab-pane>

      <el-tab-pane label="Grafana Loki" name="grafana">
        <el-card shadow="never" v-loading="integrationLoading">
          <template #header>
            <div class="grafana-header">
              <span>Grafana + Loki 日志平台</span>
              <el-button :loading="integrationLoading" @click="loadIntegrations">
                <el-icon><Refresh /></el-icon>
                刷新状态
              </el-button>
            </div>
          </template>

          <el-row :gutter="16" class="integration-stats">
            <el-col :xs="24" :sm="8">
              <el-card shadow="never" class="integration-card">
                <div class="integration-title">Grafana</div>
                <el-tag :type="integrations.grafana_online ? 'success' : 'danger'" size="small">
                  {{ integrations.grafana_online ? '在线' : '离线' }}
                </el-tag>
                <div class="integration-url">{{ integrations.grafana_url || '-' }}</div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-card shadow="never" class="integration-card">
                <div class="integration-title">Loki</div>
                <el-tag :type="integrations.loki_online ? 'success' : 'danger'" size="small">
                  {{ integrations.loki_online ? '在线' : '离线' }}
                </el-tag>
                <div class="integration-url">{{ integrations.loki_url || '-' }}</div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="8">
              <el-card shadow="never" class="integration-card">
                <div class="integration-title">代理认证</div>
                <el-tag :type="integrations.grafana_auth_ok ? 'success' : 'warning'" size="small">
                  {{ integrations.grafana_auth_ok ? '正常' : '异常' }}
                </el-tag>
                <div class="integration-url">平台账号免登 · 后端服务账号代理</div>
              </el-card>
            </el-col>
          </el-row>

          <el-alert
            v-if="integrations.grafana_online && !integrations.grafana_auth_ok"
            class="setup-alert"
            type="error"
            show-icon
            :closable="false"
            title="Grafana 自动登录失败"
          >
            <template #default>
              <p>{{ integrations.grafana_auth_message || 'Grafana 管理员密码与后端配置不一致' }}</p>
              <pre class="setup-code">docker exec ai-platform-grafana grafana-cli admin reset-admin-password '你的新密码'
grep GRAFANA_ADMIN .env.docker monitoring/.env
docker compose up -d backend</pre>
            </template>
          </el-alert>

          <el-tabs v-model="grafanaSubTab" class="grafana-sub-tabs">
            <el-tab-pane label="Loki 直查" name="loki">
              <div class="loki-toolbar">
                <el-select v-model="lokiHours" style="width: 130px">
                  <el-option label="最近 1 小时" :value="1" />
                  <el-option label="最近 6 小时" :value="6" />
                  <el-option label="最近 24 小时" :value="24" />
                </el-select>
                <el-select v-model="lokiLimit" style="width: 110px">
                  <el-option label="100 行" :value="100" />
                  <el-option label="200 行" :value="200" />
                  <el-option label="500 行" :value="500" />
                </el-select>
                <el-input
                  v-model="lokiQuery"
                  clearable
                  placeholder='LogQL，如 {job="ai-platform"}'
                  class="loki-query-input"
                  @keyup.enter="runLokiQuery"
                />
                <el-button type="primary" :loading="lokiLoading" :disabled="!integrations.loki_online" @click="runLokiQuery">
                  查询
                </el-button>
              </div>
              <div class="log-meta">
                <span>匹配: {{ lokiLines.length }} 行</span>
                <span>数据源: Loki API</span>
              </div>
              <div v-loading="lokiLoading" class="log-viewer loki-viewer">
                <div v-if="!lokiLines.length && !lokiLoading" class="empty-tip">暂无 Loki 日志，请确认 Promtail 已采集</div>
                <div
                  v-for="(line, index) in lokiLines"
                  :key="`${line.timestamp}-${index}`"
                  class="log-line"
                  :class="`level-${(line.level || 'INFO').toLowerCase()}`"
                >
                  <span class="line-no">{{ line.timestamp || '·' }}</span>
                  <span class="line-level">{{ line.source || 'loki' }}</span>
                  <span class="line-text">{{ line.text }}</span>
                </div>
              </div>
            </el-tab-pane>

            <el-tab-pane label="Grafana 仪表盘" name="dashboard">
              <div class="grafana-actions">
                <el-button type="primary" :disabled="!integrations.monitoring_online" @click="openGrafana(integrations.dashboard_url)">
                  新窗口打开仪表盘
                </el-button>
                <el-button :disabled="!integrations.monitoring_online" @click="openGrafana(integrations.explore_url)">
                  新窗口打开 Explore
                </el-button>
              </div>

              <el-alert
                v-if="!integrations.monitoring_online"
                class="setup-alert"
                type="info"
                show-icon
                :closable="false"
                title="监控栈尚未就绪"
              >
                <template #default>
                  <p>在服务器上执行：</p>
                  <pre class="setup-code">{{ integrations.startup_hint || './deploy.sh monitoring start' }}</pre>
                  <p>平台通过后端服务账号代理 Grafana，无需手动输入 Grafana 密码。</p>
                </template>
              </el-alert>

              <iframe
                v-if="showEmbed && embedUrl"
                class="grafana-embed"
                :src="embedUrl"
                title="Grafana Dashboard"
              />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { logsApi } from '@/api'

const sources = ref([])
const logDir = ref('')
const activeSource = ref('backend')
const lineCount = ref(200)
const keyword = ref('')
const levelFilter = ref('')
const loading = ref(false)
const liveMode = ref(true)
const autoScroll = ref(true)
const displayLines = ref([])
const totalMatched = ref(0)
const logContainerRef = ref(null)
const activeTab = ref('builtin')
const grafanaSubTab = ref('loki')
const integrationLoading = ref(false)
const lokiQuery = ref('{job="ai-platform"}')
const lokiHours = ref(6)
const lokiLimit = ref(200)
const lokiLoading = ref(false)
const lokiLines = ref([])
const integrations = ref({
  enabled: true,
  embed_enabled: true,
  use_proxy: true,
  grafana_url: '',
  loki_url: '',
  dashboard_url: '',
  explore_url: '',
  embed_url: '',
  grafana_online: false,
  loki_online: false,
  grafana_auth_ok: false,
  grafana_auth_message: '',
  monitoring_online: false,
  anonymous_access: false,
  startup_hint: './deploy.sh monitoring recreate-grafana',
})
const embedUrl = ref('')

let streamAbort = null
let refreshTimer = null
let integrationTimer = null

const showEmbed = computed(
  () => integrations.value.embed_enabled && integrations.value.monitoring_online && embedUrl.value
)

const sourceOptions = computed(() =>
  sources.value.map((item) => ({ label: item.label, value: item.key }))
)

function formatSize(size) {
  if (!size) return '0 B'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

async function loadSources() {
  const data = await logsApi.sources()
  sources.value = data.sources || []
  logDir.value = data.log_dir || ''
}

async function refreshLogs() {
  loading.value = true
  try {
    const data = await logsApi.tail({
      source: activeSource.value,
      lines: lineCount.value,
      keyword: keyword.value || undefined,
      level: levelFilter.value || undefined,
    })
    displayLines.value = data.lines || []
    totalMatched.value = data.total_matched || 0
    await scrollToBottom()
  } finally {
    loading.value = false
  }
}

function scrollToBottom() {
  if (!autoScroll.value) return
  nextTick(() => {
    const container = logContainerRef.value
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  })
}

function stopStream() {
  if (streamAbort) {
    streamAbort.abort()
    streamAbort = null
  }
}

async function startStream() {
  stopStream()
  await refreshLogs()
  streamAbort = new AbortController()
  const token = localStorage.getItem('token')
  const params = new URLSearchParams({ source: activeSource.value })
  try {
    const response = await fetch(`/api/v1/logs/stream?${params.toString()}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal: streamAbort.signal,
    })
    if (!response.ok) {
      throw new Error('实时日志连接失败')
    }
    const reader = response.body.getReader()
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
        const payload = JSON.parse(line.slice(5).trim())
        if (payload.type === 'line') {
          displayLines.value.push(payload)
          if (displayLines.value.length > 3000) {
            displayLines.value.splice(0, displayLines.value.length - 3000)
          }
          totalMatched.value += 1
          scrollToBottom()
        }
      }
    }
  } catch (error) {
    if (error.name !== 'AbortError') {
      ElMessage.warning(error.message || '实时日志连接中断')
    }
  }
}

function handleLiveToggle(enabled) {
  if (enabled) {
    startStream()
  } else {
    stopStream()
    refreshLogs()
  }
}

function switchSource(source) {
  if (activeSource.value === source) return
  activeSource.value = source
  handleSourceChange(source)
}

function handleSourceChange() {
  stopStream()
  displayLines.value = []
  if (liveMode.value) {
    startStream()
  } else {
    refreshLogs()
  }
}

async function downloadLog() {
  const token = localStorage.getItem('token')
  const params = new URLSearchParams({ source: activeSource.value })
  const response = await fetch(`/api/v1/logs/download?${params.toString()}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    ElMessage.error('下载失败')
    return
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${activeSource.value}.log`
  link.click()
  URL.revokeObjectURL(url)
}

const originParams = () => ({
  public_host: window.location.hostname,
  public_origin: window.location.origin,
})

const GRAFANA_PROXY_PREFIX = '/api/v1/logs/grafana'
const EMBED_QUERY_PARAM = '_pt'

function buildGrafanaProxyUrl(redirect, embedToken = '') {
  const path = redirect.startsWith('/') ? redirect : `/${redirect}`
  let url = `${window.location.origin}${GRAFANA_PROXY_PREFIX}${path}`
  if (embedToken) {
    url += `${path.includes('?') ? '&' : '?'}${EMBED_QUERY_PARAM}=${encodeURIComponent(embedToken)}`
  }
  return url
}

async function ensureGrafanaSession() {
  return logsApi.grafanaSession()
}

async function runLokiQuery() {
  if (!integrations.value.loki_online) return
  lokiLoading.value = true
  try {
    const data = await logsApi.lokiQuery({
      query: lokiQuery.value || undefined,
      limit: lokiLimit.value,
      hours: lokiHours.value,
    })
    lokiLines.value = data.lines || []
  } finally {
    lokiLoading.value = false
  }
}

async function loadIntegrations() {
  integrationLoading.value = true
  try {
    integrations.value = await logsApi.integrations(originParams())
    embedUrl.value = ''
    if (integrations.value.monitoring_online && integrations.value.embed_url) {
      if (integrations.value.use_proxy) {
        const session = await ensureGrafanaSession()
        embedUrl.value = buildGrafanaProxyUrl(
          integrations.value.embed_url,
          session?.embed_token || '',
        )
      } else {
        embedUrl.value = integrations.value.embed_url
      }
    }
    if (integrations.value.loki_online && !lokiLines.value.length) {
      await runLokiQuery()
    }
  } finally {
    integrationLoading.value = false
  }
}

async function openGrafana(redirect) {
  if (!redirect) return
  if (integrations.value.use_proxy) {
    const session = await ensureGrafanaSession()
    window.open(
      buildGrafanaProxyUrl(redirect, session?.embed_token || ''),
      '_blank',
      'noopener,noreferrer',
    )
    return
  }
  window.open(redirect, '_blank', 'noopener,noreferrer')
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([loadSources(), loadIntegrations()])
    if (liveMode.value) {
      await startStream()
    } else {
      await refreshLogs()
    }
    refreshTimer = window.setInterval(async () => {
      await loadSources()
      if (!liveMode.value) {
        await refreshLogs()
      }
    }, 10000)
    integrationTimer = window.setInterval(loadIntegrations, 15000)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  stopStream()
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
  if (integrationTimer) {
    clearInterval(integrationTimer)
  }
})
</script>

<style scoped>
.log-monitor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-row {
  margin-bottom: 0;
}

.stat-card {
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.stat-card.active {
  border-color: #409eff;
  box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.15);
}

.stat-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.stat-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  color: #606266;
  font-size: 13px;
  margin-bottom: 8px;
}

.stat-path,
.stat-time {
  color: #909399;
  font-size: 12px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.log-meta {
  display: flex;
  gap: 16px;
  color: #909399;
  font-size: 12px;
  margin-bottom: 12px;
}

.live-dot {
  color: #67c23a;
}

.live-dot::before {
  content: '●';
  margin-right: 4px;
}

.log-viewer {
  height: 560px;
  overflow: auto;
  background: #0f172a;
  border-radius: 8px;
  padding: 12px;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.empty-tip {
  color: #94a3b8;
  text-align: center;
  padding: 48px 0;
}

.log-line {
  display: grid;
  grid-template-columns: 56px 72px 1fr;
  gap: 10px;
  padding: 2px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
}

.line-no,
.line-level {
  color: #64748b;
}

.line-text {
  color: #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
}

.level-error .line-level,
.level-error .line-text {
  color: #f87171;
}

.level-warn .line-level,
.level-warn .line-text {
  color: #fbbf24;
}

.level-info .line-level,
.level-info .line-text {
  color: #93c5fd;
}

.level-debug .line-level,
.level-debug .line-text {
  color: #86efac;
}

.monitor-tabs {
  --el-tabs-header-height: 44px;
}

.grafana-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.integration-stats {
  margin-bottom: 16px;
}

.integration-card {
  min-height: 110px;
}

.integration-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
}

.integration-url {
  margin-top: 10px;
  color: #909399;
  font-size: 12px;
  word-break: break-all;
}

.grafana-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.setup-alert {
  margin-bottom: 16px;
}

.setup-code {
  margin: 8px 0;
  padding: 10px 12px;
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 6px;
  font-family: Consolas, Monaco, 'Courier New', monospace;
}

.grafana-embed {
  width: 100%;
  height: 720px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #111;
}

.grafana-sub-tabs {
  margin-top: 4px;
}

.loki-toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.loki-query-input {
  flex: 1;
  min-width: 260px;
}

.loki-viewer {
  height: 620px;
}
</style>

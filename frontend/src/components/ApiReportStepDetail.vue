<template>
  <div class="report-step-detail">
    <div v-if="step.error_message" class="step-error">
      <el-alert :title="step.error_message" type="error" show-icon :closable="false" />
    </div>

    <div class="step-url-bar">
      <span :class="['method-badge', methodClass]">{{ step.method }}</span>
      <code class="step-url">{{ step.url }}</code>
      <div class="step-url-meta">
        <span v-if="step.response_status != null" :class="['http-status', httpStatusClass]">
          {{ step.response_status }}
        </span>
        <span class="step-time">{{ formatDuration(step.duration_ms) }}</span>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="step-detail-tabs">
      <el-tab-pane label="请求" name="request">
        <div class="detail-section">
          <div class="section-head">
            <span class="section-title">请求头</span>
            <span v-if="requestHeaderRows.length" class="section-count">{{ requestHeaderRows.length }} 项</span>
          </div>
          <el-table
            v-if="requestHeaderRows.length"
            :data="requestHeaderRows"
            size="small"
            stripe
            class="kv-table"
          >
            <el-table-column prop="key" label="Header" min-width="160" />
            <el-table-column prop="value" label="值" min-width="240" show-overflow-tooltip />
          </el-table>
          <pre v-else class="code-viewer empty">{{ prettyText(step.request_headers) }}</pre>
        </div>

        <div class="detail-section">
          <div class="section-head">
            <span class="section-title">请求体</span>
          </div>
          <pre class="code-viewer" :class="{ empty: !hasRequestBody }">{{ prettyText(step.request_body) }}</pre>
        </div>
      </el-tab-pane>

      <el-tab-pane label="响应" name="response">
        <div class="response-summary">
          <div class="summary-item">
            <span class="summary-item-label">状态码</span>
            <span v-if="step.response_status != null" :class="['http-status', 'http-status-lg', httpStatusClass]">
              {{ step.response_status }}
            </span>
            <span v-else class="text-muted">-</span>
          </div>
          <div class="summary-item">
            <span class="summary-item-label">耗时</span>
            <span class="summary-item-value">{{ formatDuration(step.duration_ms) }}</span>
          </div>
        </div>

        <div class="detail-section">
          <div class="section-head">
            <span class="section-title">响应头</span>
            <span v-if="responseHeaderRows.length" class="section-count">{{ responseHeaderRows.length }} 项</span>
          </div>
          <el-table
            v-if="responseHeaderRows.length"
            :data="responseHeaderRows"
            size="small"
            stripe
            class="kv-table"
          >
            <el-table-column prop="key" label="Header" min-width="160" />
            <el-table-column prop="value" label="值" min-width="240" show-overflow-tooltip />
          </el-table>
          <pre v-else class="code-viewer empty">{{ prettyText(step.response_headers) }}</pre>
        </div>

        <div class="detail-section">
          <div class="section-head">
            <span class="section-title">响应体</span>
          </div>
          <pre class="code-viewer" :class="{ empty: !hasResponseBody }">{{ prettyText(step.response_body) }}</pre>
        </div>
      </el-tab-pane>

      <el-tab-pane :label="assertionTabLabel" name="assertions">
        <el-empty v-if="!assertionRows.length" description="暂无断言" :image-size="56" />
        <el-table v-else :data="assertionRows" size="small" stripe class="assertion-table">
          <el-table-column label="结果" width="72" align="center">
            <template #default="{ row }">
              <el-tag :type="row.passed ? 'success' : 'danger'" size="small" effect="light">
                {{ row.passed ? '通过' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="message" label="说明" min-width="180" show-overflow-tooltip />
          <el-table-column label="期望" min-width="120">
            <template #default="{ row }">{{ formatValue(row.expected) }}</template>
          </el-table-column>
          <el-table-column label="实际" min-width="120">
            <template #default="{ row }">{{ formatValue(row.actual) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  step: { type: Object, required: true },
})

const activeTab = ref('request')

const methodClass = computed(() => {
  const method = (props.step.method || '').toUpperCase()
  return {
    GET: 'method-get',
    POST: 'method-post',
    PUT: 'method-put',
    PATCH: 'method-patch',
    DELETE: 'method-delete',
  }[method] || 'method-default'
})

const httpStatusClass = computed(() => {
  const code = Number(props.step.response_status)
  if (!code) return 'status-unknown'
  if (code >= 200 && code < 300) return 'status-success'
  if (code >= 300 && code < 400) return 'status-redirect'
  if (code >= 400 && code < 500) return 'status-client'
  if (code >= 500) return 'status-server'
  return 'status-unknown'
})

const requestHeaderRows = computed(() => parseHeaderRows(props.step.request_headers))
const responseHeaderRows = computed(() => parseHeaderRows(props.step.response_headers))
const assertionRows = computed(() => props.step.assertion_results || [])

const assertionTabLabel = computed(() => {
  const count = assertionRows.value.length
  return count ? `断言 (${count})` : '断言'
})

const hasRequestBody = computed(() => Boolean(String(props.step.request_body || '').trim()))
const hasResponseBody = computed(() => Boolean(String(props.step.response_body || '').trim()))

function parseHeaderRows(text) {
  if (!text) return []
  try {
    const parsed = JSON.parse(text)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return []
    return Object.entries(parsed).map(([key, value]) => ({
      key,
      value: value == null ? '' : String(value),
    }))
  } catch {
    return []
  }
}

function prettyText(text) {
  const raw = String(text ?? '').trim()
  if (!raw) return '-'
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}

function formatDuration(ms) {
  if (!ms && ms !== 0) return '-'
  if (ms < 1000) return `${Math.round(ms)}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

function formatValue(value) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>

<style scoped>
.report-step-detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.step-error {
  margin-bottom: 2px;
}

.step-url-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}

.method-badge {
  flex-shrink: 0;
  min-width: 52px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
  letter-spacing: 0.02em;
}

.method-get { background: #dcfce7; color: #166534; }
.method-post { background: #dbeafe; color: #1d4ed8; }
.method-put { background: #fef3c7; color: #b45309; }
.method-patch { background: #e0e7ff; color: #4338ca; }
.method-delete { background: #fee2e2; color: #b91c1c; }
.method-default { background: #f1f5f9; color: #475569; }

.step-url {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: #334155;
  word-break: break-all;
  line-height: 1.5;
  background: transparent;
}

.step-url-meta {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.step-time {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.http-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 42px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.http-status-lg {
  min-width: 52px;
  padding: 4px 12px;
  font-size: 14px;
}

.status-success { background: #dcfce7; color: #15803d; }
.status-redirect { background: #dbeafe; color: #1d4ed8; }
.status-client { background: #ffedd5; color: #c2410c; }
.status-server { background: #fee2e2; color: #b91c1c; }
.status-unknown { background: #f1f5f9; color: #64748b; }

.step-detail-tabs :deep(.el-tabs__header) {
  margin-bottom: 12px;
}

.step-detail-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: #e2e8f0;
}

.detail-section + .detail-section {
  margin-top: 16px;
}

.section-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.section-count {
  font-size: 12px;
  color: #94a3b8;
}

.response-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  padding: 12px 14px;
  background: #fafbfc;
  border: 1px solid #edf2f7;
  border-radius: 8px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-item-label {
  font-size: 12px;
  color: #64748b;
}

.summary-item-value {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.kv-table {
  border-radius: 8px;
  overflow: hidden;
}

.kv-table :deep(.el-table__header th) {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
}

.code-viewer {
  margin: 0;
  padding: 14px 16px;
  max-height: 360px;
  overflow: auto;
  border-radius: 8px;
  background: #0f172a;
  color: #e2e8f0;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid #1e293b;
}

.code-viewer.empty {
  color: #94a3b8;
  background: #f8fafc;
  border-color: #e2e8f0;
}

.assertion-table {
  border-radius: 8px;
  overflow: hidden;
}

.text-muted {
  color: #94a3b8;
}
</style>

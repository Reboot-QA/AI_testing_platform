<template>
  <div class="step-detail">
    <div v-if="step.error_message" class="err-box">{{ step.error_message }}</div>

    <el-alert
      v-for="(w, i) in step.warnings || []"
      :key="'w' + i"
      :title="w"
      type="warning"
      :closable="false"
      show-icon
      class="step-warn"
    />

    <div v-if="step.url" class="detail-toolbar">
      <span class="detail-toolbar__label">HTTP 响应</span>
      <el-tag size="small" :type="statusTag">{{ step.response_status ?? '—' }}</el-tag>
      <span class="detail-toolbar__meta">{{ formatReportDuration(step.duration_ms) }}</span>
    </div>

    <el-tabs v-if="hasTabs" v-model="activeTab" class="detail-tabs">
      <el-tab-pane v-if="step.url" label="实际请求" name="request">
        <div class="detail-panel">
          <ActualRequestView
            :method="step.method"
            :url="step.url"
            :headers="step.request_headers"
            :body="step.request_body"
          />
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="step.response_body" label="响应 Body" name="body">
        <div class="detail-panel detail-panel--code">
          <JsonView :data="step.response_body" :deep="4" />
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="hasRespHeaders" label="响应 Headers" name="respHeaders">
        <div class="detail-panel detail-panel--code">
          <JsonView :data="step.response_headers" :deep="2" />
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="assertionCount" :label="`断言 (${assertionCount})`" name="assertions">
        <ResultList :items="assertionItems" />
      </el-tab-pane>

      <el-tab-pane v-if="step.contract_result" label="契约校验" name="contract">
        <ResultList :items="[contractItem]" />
        <div v-for="(err, i) in step.contract_result.errors || []" :key="'c' + i" class="mono-line">
          {{ err }}
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="extractCount" :label="`提取 (${extractCount})`" name="extracts">
        <ResultList :items="extractItems" />
      </el-tab-pane>

      <el-tab-pane v-if="step.url" label="控制台" name="logs">
        <div class="detail-panel detail-panel--code">
          <template v-if="(step.script_logs || []).length">
            <div v-for="(l, i) in step.script_logs || []" :key="'l' + i" class="mono-line">
              {{ l }}
            </div>
          </template>
          <span v-else class="empty-hint">没有内容</span>
        </div>
      </el-tab-pane>

      <el-tab-pane v-if="step.url" label="Cookie" name="cookies">
        <div class="detail-panel">
          <CookieView
            :request-headers="step.request_headers"
            :response-headers="step.response_headers"
          />
        </div>
      </el-tab-pane>
    </el-tabs>

    <div v-else class="detail-fallback">
      <template v-if="assertionCount">
        <div class="fallback-title">断言</div>
        <ResultList :items="assertionItems" />
      </template>
      <template v-if="extractCount">
        <div class="fallback-title">提取</div>
        <ResultList :items="extractItems" />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Schemas } from '@/api/types'
import JsonView from '@/components/apifox/common/JsonView.vue'
import ActualRequestView from '@/components/apifox/endpoint/ActualRequestView.vue'
import CookieView from '@/components/apifox/endpoint/CookieView.vue'
import ResultList from '@/components/apifox/run/RunStepResultList.vue'
import { toAssertionItems } from '@/utils/assertionItems'
import { formatReportDuration } from '@/utils/runReportStats'

const props = defineProps<{ step: Schemas['RunStepOut'] }>()

const activeTab = ref('request')

const statusTag = computed(() => {
  const s = props.step.response_status
  if (s == null) return 'info'
  return s >= 200 && s < 400 ? 'success' : 'danger'
})

const assertionItems = computed(() =>
  toAssertionItems(props.step.assertion_results, props.step.script_logs),
)
const assertionCount = computed(() => assertionItems.value.length)
const extractCount = computed(() => (props.step.extract_results || []).length)

const hasRespHeaders = computed(() => {
  const h = props.step.response_headers
  return !!h && typeof h === 'object' && Object.keys(h).length > 0
})

const hasTabs = computed(
  () =>
    !!props.step.url ||
    !!props.step.response_body ||
    hasRespHeaders.value ||
    assertionCount.value > 0 ||
    extractCount.value > 0 ||
    !!props.step.contract_result,
)

const extractItems = computed(() =>
  (props.step.extract_results || []).map((e) => ({
    passed: !!e.passed,
    label: e.passed ? '成功' : '失败',
    message: `${e.var_name} = ${e.value || e.message}（${e.scope}）`,
  })),
)

const contractItem = computed(() => {
  const c = props.step.contract_result
  if (!c) return { passed: false, label: '', message: '' }
  return {
    passed: !!c.passed,
    label: c.passed ? '符合' : '不符',
    message: `${c.schema_name} · ${c.message}`,
  }
})

watch(
  () => props.step.id,
  () => {
    activeTab.value = props.step.url ? 'request' : assertionCount.value ? 'assertions' : 'body'
  },
  { immediate: true },
)
</script>

<style scoped>
.step-detail {
  padding: var(--ax-space-3) var(--ax-space-4);
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--color-purple-6) 4%, var(--ax-bg-subtle)) 0%,
    var(--ax-bg-subtle) 48px
  );
  border-top: 1px solid var(--ax-border);
  border-left: 3px solid color-mix(in srgb, var(--color-purple-6) 35%, var(--ax-border));
}

.err-box {
  padding: var(--ax-space-2) var(--ax-space-3);
  margin-bottom: var(--ax-space-2);
  border-radius: var(--ax-radius-sm);
  background: color-mix(in srgb, var(--color-pink-6) 8%, var(--ax-bg));
  border: 1px solid color-mix(in srgb, var(--color-pink-6) 25%, var(--ax-border));
  color: var(--color-pink-6);
  font-size: var(--ax-font-sm);
}

.step-warn {
  margin-bottom: var(--ax-space-2);
}

.detail-toolbar {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
  padding: var(--ax-space-1-5) var(--ax-space-2);
  border-radius: var(--ax-radius-sm);
  background: var(--ax-bg);
  border: 1px solid var(--ax-border);
}

.detail-toolbar__label {
  font-size: var(--ax-font-xs);
  font-weight: 600;
  color: var(--ax-text-secondary);
}

.detail-toolbar__meta {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
  font-variant-numeric: tabular-nums;
}

.detail-tabs :deep(.el-tabs__header) {
  margin-bottom: var(--ax-space-2);
}

.detail-tabs :deep(.el-tabs__item) {
  font-size: var(--ax-font-sm);
  padding: 0 var(--ax-space-3);
}

.detail-panel {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-sm);
  background: var(--ax-bg);
  padding: var(--ax-space-3);
  max-height: 420px;
  overflow: auto;
}

.detail-panel--code {
  padding: var(--ax-space-2);
  background: color-mix(in srgb, var(--ax-bg-subtle) 80%, var(--ax-bg));
}

.mono-line {
  font-family: Consolas, Monaco, monospace;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-secondary);
  padding: var(--ax-space-1) 0;
  line-height: 1.5;
}

.empty-hint {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-sm);
}

.detail-fallback {
  padding-top: var(--ax-space-1);
}

.fallback-title {
  font-size: var(--ax-font-sm);
  font-weight: 600;
  color: var(--ax-text-secondary);
  margin: var(--ax-space-2) 0 var(--ax-space-1);
}
</style>

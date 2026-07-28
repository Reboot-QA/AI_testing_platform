<template>
  <div class="debug-resp">
    <div class="debug-resp__toolbar">
      <span class="debug-resp__switch-lbl">控制台打印结果</span>
      <el-tooltip content="开启后，可在控制台中将 SQL 查询到的结果打印展示出来" placement="top">
        <el-icon class="debug-resp__info"><InfoFilled /></el-icon>
      </el-tooltip>
      <el-switch v-model="consolePrintDbEnabled" size="small" />
    </div>

    <template v-if="resp">
      <div class="debug-resp__head">
        <span class="debug-resp__lbl">响应</span>
        <el-tag size="small" :type="statusType">{{ resp.status_code ?? '—' }}</el-tag>
        <el-tag v-if="statusHint" size="small" type="danger" effect="plain">{{
          statusHint
        }}</el-tag>
        <span class="debug-resp__meta">{{ Math.round(resp.duration_ms) }} ms</span>
        <span v-if="resp.error" class="debug-resp__err">{{ resp.error }}</span>
      </div>
      <el-alert
        v-for="(w, i) in resp.warnings || []"
        :key="'w' + i"
        :title="w"
        type="warning"
        :closable="false"
        show-icon
        class="debug-resp__warn"
      />
      <el-tabs v-model="activeTab" class="debug-resp__tabs">
        <el-tab-pane label="实际请求" name="request">
          <div class="debug-resp__box">
            <ActualRequestView
              :method="resp.method"
              :url="resp.url"
              :headers="resp.request_headers"
              :body="resp.request_body"
            />
          </div>
        </el-tab-pane>
        <el-tab-pane label="响应 Body" name="body">
          <div class="debug-resp__box"><JsonView :data="resp.response_body" :deep="3" /></div>
        </el-tab-pane>
        <el-tab-pane label="响应 Headers" name="headers">
          <div class="debug-resp__box"><JsonView :data="resp.response_headers" :deep="2" /></div>
        </el-tab-pane>
        <el-tab-pane label="Cookie" name="cookies">
          <div class="debug-resp__box">
            <CookieView
              :request-headers="resp.request_headers"
              :response-headers="resp.response_headers"
            />
          </div>
        </el-tab-pane>
        <el-tab-pane v-if="assertionItems.length" label="断言" name="assertions">
          <div class="debug-resp__box"><ResultList :items="assertionItems" /></div>
        </el-tab-pane>
        <el-tab-pane v-if="resp.extract_results?.length" label="提取" name="extracts">
          <div v-for="(e, i) in resp.extract_results" :key="'e' + i" class="debug-resp__line">
            <el-tag size="small" :type="e.passed ? 'success' : 'danger'">
              {{ e.passed ? '成' : '败' }}
            </el-tag>
            {{ e.var_name }} = {{ e.value || e.message }}（{{ e.scope }}）
          </div>
        </el-tab-pane>
        <el-tab-pane :label="consoleTabLabel" name="logs">
          <div class="debug-resp__box console-pane">
            <template v-if="hasConsoleContent">
              <div
                v-for="(entry, i) in resp.console_db_logs || []"
                :key="'db' + i"
                class="console-db"
              >
                <div class="console-db__head">
                  <span class="console-db__time">{{ entry.time }}</span>
                  <span class="console-db__sql mono">{{ entry.sql }}</span>
                </div>
                <p v-if="!entry.passed && entry.error" class="console-db__err">{{ entry.error }}</p>
                <JsonView v-else-if="entry.rows?.length" :data="entry.rows" :deep="4" />
                <p v-else class="console-db__meta">影响行数：{{ entry.row_count }}</p>
              </div>
              <div v-for="(l, i) in resp.script_logs" :key="'l' + i" class="debug-resp__line mono">
                {{ l }}
              </div>
            </template>
            <span v-else class="empty-console">没有内容</span>
          </div>
        </el-tab-pane>
        <el-tab-pane v-if="resp.contract_result" label="契约" name="contract">
          <div class="debug-resp__line">
            <el-tag size="small" :type="resp.contract_result.passed ? 'success' : 'danger'">
              {{ resp.contract_result.passed ? '符合' : '不符' }}
            </el-tag>
            {{ resp.contract_result.schema_name }} · {{ resp.contract_result.message }}
          </div>
          <div
            v-for="(err, i) in resp.contract_result.errors"
            :key="'c' + i"
            class="debug-resp__line mono"
          >
            {{ err }}
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'
import type { Schemas } from '@/api/types'
import { useDebugConsolePrint } from '@/composables/useDebugConsolePrint'
import JsonView from '@/components/apifox/common/JsonView.vue'
import ActualRequestView from '@/components/apifox/endpoint/ActualRequestView.vue'
import CookieView from '@/components/apifox/endpoint/CookieView.vue'
import ResultList from '@/components/apifox/run/RunStepResultList.vue'
import { toAssertionItems } from '@/utils/assertionItems'
import { httpStatusHint } from '@/utils/httpStatusHint'

const props = defineProps<{ resp: Schemas['DebugResponse'] | null }>()

// 声明式断言 + 脚本断言(pm.test 的 ✓/✗)合并展示，失败补出期望/实际（7/23-#8）
const assertionItems = computed(() =>
  toAssertionItems(props.resp?.assertion_results, props.resp?.script_logs),
)

const { enabled: consolePrintDbEnabled } = useDebugConsolePrint()
const activeTab = ref('body')

const statusType = computed(() => {
  const s = props.resp?.status_code
  if (s == null) return 'info'
  return s >= 200 && s < 400 ? 'success' : 'danger'
})

const statusHint = computed(() =>
  httpStatusHint(props.resp?.status_code, props.resp?.response_body),
)

const consoleCount = computed(() => {
  const r = props.resp
  if (!r) return 0
  return (r.script_logs?.length || 0) + (r.console_db_logs?.length || 0)
})

const consoleTabLabel = computed(() =>
  consoleCount.value > 0 ? `控制台 (${consoleCount.value})` : '控制台',
)

const hasConsoleContent = computed(() => {
  const r = props.resp
  if (!r) return false
  return (r.script_logs?.length || 0) > 0 || (r.console_db_logs?.length || 0) > 0
})

watch(
  () => props.resp,
  (r) => {
    activeTab.value = 'body'
    if (r?.console_db_logs?.length) {
      activeTab.value = 'logs'
    }
  },
)

defineExpose({ consolePrintEnabled: consolePrintDbEnabled })
</script>

<style scoped>
.debug-resp {
  margin-top: var(--ax-space-3);
  border-top: 1px solid var(--ax-border);
  padding-top: var(--ax-space-2-5);
}

.debug-resp__toolbar {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  margin-bottom: var(--ax-space-2);
}

.debug-resp__switch-lbl {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.debug-resp__info {
  color: var(--ax-text-placeholder);
  cursor: help;
}

.debug-resp__head {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.debug-resp__lbl {
  font-weight: 600;
  color: var(--ax-brand);
}

.debug-resp__meta {
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-xs);
}

.debug-resp__err {
  color: var(--ax-danger);
  font-size: var(--ax-font-xs);
}

.debug-resp__warn {
  margin: var(--ax-space-2) 0;
}

.debug-resp__box {
  max-height: 320px;
  overflow: auto;
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  padding: var(--ax-space-2);
}

.console-pane {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
}

.console-db {
  border-bottom: 1px solid var(--ax-border);
  padding-bottom: var(--ax-space-2);
}

.console-db:last-child {
  border-bottom: none;
}

.console-db__head {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-1);
  font-size: var(--ax-font-sm);
}

.console-db__time {
  color: var(--ax-text-placeholder);
  flex-shrink: 0;
}

.console-db__sql {
  color: var(--ax-text-secondary);
  word-break: break-all;
}

.console-db__err {
  color: var(--ax-danger);
  font-size: var(--ax-font-sm);
}

.console-db__meta {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}

.debug-resp__line {
  font-size: var(--ax-font-sm);
  padding: var(--ax-space-1) 0;
}

.mono {
  font-family: Consolas, Monaco, monospace;
  color: var(--ax-text-secondary);
}

.empty-console {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-sm);
}
</style>

<template>
  <div class="debug-panel">
    <div class="send-bar">
      <el-button type="success" size="small" :loading="sending" @click="send">发送</el-button>
      <span class="hint">直接发一次请求（不建用例、不落报告）· 环境在顶部选择</span>
    </div>

    <ApiEndpointEditor
      :form="form"
      :saving="saving"
      :server-names="serverNames"
      :project-id="projectId"
      show-processors
      :scripts="scripts"
      :schemas="schemas"
      @save="$emit('save')"
    />

    <div v-if="resp" class="resp">
      <div class="resp-head">
        <span class="lbl">响应</span>
        <el-tag size="small" :type="statusType">{{ resp.status_code ?? '—' }}</el-tag>
        <span class="meta">{{ Math.round(resp.duration_ms) }} ms</span>
        <span v-if="resp.error" class="err">{{ resp.error }}</span>
      </div>
      <el-alert
        v-for="(w, i) in resp.warnings || []"
        :key="'w' + i"
        :title="w"
        type="warning"
        :closable="false"
        show-icon
        class="warn"
      />
      <el-tabs v-model="respTab" class="resp-tabs">
        <el-tab-pane label="实际请求" name="request">
          <div class="resp-box">
            <ActualRequestView
              :method="resp.method"
              :url="resp.url"
              :headers="resp.request_headers"
              :body="resp.request_body"
            />
          </div>
        </el-tab-pane>
        <el-tab-pane label="响应 Body" name="body">
          <div class="resp-box"><JsonView :data="resp.response_body" :deep="3" /></div>
        </el-tab-pane>
        <el-tab-pane label="响应 Headers" name="headers">
          <div class="resp-box"><JsonView :data="resp.response_headers" :deep="2" /></div>
        </el-tab-pane>
        <el-tab-pane v-if="resp.assertion_results?.length" label="断言" name="assertions">
          <div v-for="(a, i) in resp.assertion_results" :key="'a' + i" class="line">
            <el-tag size="small" :type="a.passed ? 'success' : 'danger'">{{
              a.passed ? '过' : '败'
            }}</el-tag>
            {{ a.message }}
          </div>
        </el-tab-pane>
        <el-tab-pane v-if="resp.extract_results?.length" label="提取" name="extracts">
          <div v-for="(e, i) in resp.extract_results" :key="'e' + i" class="line">
            <el-tag size="small" :type="e.passed ? 'success' : 'danger'">{{
              e.passed ? '成' : '败'
            }}</el-tag>
            {{ e.var_name }} = {{ e.value || e.message }}（{{ e.scope }}）
          </div>
        </el-tab-pane>
        <el-tab-pane v-if="resp.script_logs?.length" label="脚本日志" name="logs">
          <div v-for="(l, i) in resp.script_logs" :key="'l' + i" class="line mono">{{ l }}</div>
        </el-tab-pane>
        <el-tab-pane v-if="resp.contract_result" label="契约" name="contract">
          <div class="line">
            <el-tag size="small" :type="resp.contract_result.passed ? 'success' : 'danger'">
              {{ resp.contract_result.passed ? '符合' : '不符' }}
            </el-tag>
            {{ resp.contract_result.schema_name }} · {{ resp.contract_result.message }}
          </div>
          <div v-for="(err, i) in resp.contract_result.errors" :key="'c' + i" class="line mono">
            {{ err }}
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { processorsToLegacy } from '@/utils/caseProcessors'
import ApiEndpointEditor from '@/components/apifox/ApiEndpointEditor.vue'
import JsonView from '@/components/apifox/common/JsonView.vue'
import ActualRequestView from '@/components/apifox/ActualRequestView.vue'
import type { EndpointEditorForm } from '@/types/apifox'

type ScriptBrief = Schemas['ScriptBrief']
type SchemaBrief = Schemas['SchemaBrief']
type DebugSendResult = Schemas['DebugResponse']

const props = withDefaults(
  defineProps<{
    form: EndpointEditorForm
    saving?: boolean
    serverNames?: string[]
    projectId: Id
    scripts?: ScriptBrief[]
    schemas?: SchemaBrief[]
  }>(),
  {
    saving: false,
    serverNames: () => [],
    scripts: () => [],
    schemas: () => [],
  },
)
defineEmits<{ save: [] }>()

const store = useWorkspaceStore()
const sending = ref(false)
const resp = ref<DebugSendResult | null>(null)
const respTab = ref('body')

const statusType = computed(() => {
  const s = resp.value?.status_code
  if (s == null) return 'info'
  return s >= 200 && s < 400 ? 'success' : 'danger'
})

async function send() {
  sending.value = true
  try {
    // debug 直发仍用旧管线：从当前有序处理器实时派生（wait/顺序在快速直发里忽略）
    const legacy = processorsToLegacy(
      props.form.pre_processors || [],
      props.form.post_processors || [],
    )
    resp.value = await apifoxApi.debugSend(props.projectId, {
      method: props.form.method,
      path: props.form.path,
      server_name: props.form.server_name,
      request_spec: props.form.request_spec as Schemas['DebugRequest']['request_spec'],
      environment_id: store.currentEnvironmentId,
      assertions: legacy.assertions as Schemas['DebugRequest']['assertions'],
      extracts: legacy.extracts as Schemas['DebugRequest']['extracts'],
      pre_scripts: legacy.pre_scripts as Schemas['DebugRequest']['pre_scripts'],
      post_scripts: legacy.post_scripts as Schemas['DebugRequest']['post_scripts'],
      response_schema_id: legacy.response_schema_id,
    })
    respTab.value = 'body'
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '发送失败')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.send-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.hint {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-xs);
}

.resp {
  margin-top: 14px;
  border-top: 1px solid var(--ax-border);
  padding-top: 10px;
}

.resp-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.lbl {
  font-weight: 600;
  color: var(--ax-brand);
}

.meta {
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-xs);
}

.err {
  color: var(--ax-danger);
  font-size: var(--ax-font-xs);
}

.resp-box {
  max-height: 320px;
  overflow: auto;
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  padding: 8px;
}

.line {
  font-size: var(--ax-font-sm);
  padding: 3px 0;
}

.mono {
  font-family: Consolas, Monaco, monospace;
  color: var(--ax-text-secondary);
}

.warn {
  margin-bottom: 8px;
}
</style>

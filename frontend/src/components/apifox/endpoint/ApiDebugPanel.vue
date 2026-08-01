<template>
  <div class="debug-panel">
    <ApiEndpointEditor
      :form="form"
      :saving="saving"
      :server-names="serverNames"
      :project-id="projectId"
      show-processors
      :scripts="scripts"
      :schemas="schemas"
      @save="$emit('save')"
    >
      <template #actions>
        <el-button type="success" size="small" :loading="sending" @click="send">发送</el-button>
      </template>
    </ApiEndpointEditor>

    <DebugResponsePanel :resp="resp" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { useApiTabsStore } from '@/stores/apiTabs'
import { useResolvableVarsReload } from '@/composables/useResolvableVars'
import { processorsToLegacy } from '@/utils/caseProcessors'
import { useDebugConsolePrint } from '@/composables/useDebugConsolePrint'
import ApiEndpointEditor from '@/components/apifox/endpoint/ApiEndpointEditor.vue'
import DebugResponsePanel from '@/components/apifox/endpoint/DebugResponsePanel.vue'
import type { EndpointEditorForm } from '@/types/apifox'

type ScriptBrief = Schemas['ScriptBrief']
type SchemaBrief = Schemas['SchemaBrief']

const props = withDefaults(
  defineProps<{
    form: EndpointEditorForm
    endpointId: number
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
const tabsStore = useApiTabsStore()
const { enabled: consolePrintDbEnabled } = useDebugConsolePrint()
const reloadResolvableVars = useResolvableVarsReload()
const sending = ref(false)
// 切走再切回会重挂载本组件：从 tab 恢复上次调试响应，避免请求信息丢失（7/23-#5）
const resp = ref<Schemas['DebugResponse'] | null>(
  tabsStore.findTab(props.projectId, props.endpointId)?.debugResp ?? null,
)

async function send() {
  sending.value = true
  try {
    const legacy = processorsToLegacy(
      props.form.pre_processors || [],
      props.form.post_processors || [],
    )
    resp.value = await apifoxApi.debugSend(props.projectId, {
      method: props.form.method,
      path: props.form.path,
      server_name: props.form.server_name || null,
      request_spec: props.form.request_spec as Schemas['DebugRequest']['request_spec'],
      environment_id: store.currentEnvironmentId,
      pre_processors: props.form.pre_processors,
      post_processors: props.form.post_processors,
      console_print_db: consolePrintDbEnabled.value,
      assertions: legacy.assertions as Schemas['DebugRequest']['assertions'],
      extracts: legacy.extracts as Schemas['DebugRequest']['extracts'],
      pre_scripts: legacy.pre_scripts as Schemas['DebugRequest']['pre_scripts'],
      post_scripts: legacy.post_scripts as Schemas['DebugRequest']['post_scripts'],
      pre_inline: legacy.pre_inline as Schemas['DebugRequest']['pre_inline'],
      post_inline: legacy.post_inline as Schemas['DebugRequest']['post_inline'],
      pre_waits: legacy.pre_waits,
      post_waits: legacy.post_waits,
      response_schema_id: legacy.response_schema_id,
    })
    tabsStore.setDebugResp(props.projectId, props.endpointId, resp.value) // 存到 tab，切走切回可恢复
    if (resp.value.extract_results?.some((r) => r.passed && r.scope !== 'temporary')) {
      await reloadResolvableVars()
    }
  } catch {
    // 错误详情已由全局响应拦截器统一提示，这里不再重复弹，避免「两个错误」（7/23-#13）
  } finally {
    sending.value = false
  }
}
</script>

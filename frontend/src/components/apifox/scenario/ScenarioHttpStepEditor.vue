<template>
  <div class="scenario-http-editor">
    <ApiEndpointEditor
      :form="config"
      :show-save="false"
      show-meta
      :server-names="serverNames"
      :project-id="projectId"
    >
      <template #actions>
        <el-button type="success" size="small" :loading="sending" @click="send">发送</el-button>
      </template>
    </ApiEndpointEditor>
    <p class="send-hint">直接发送当前步骤请求（不落报告）· 环境在顶部选择</p>
    <DebugResponsePanel :resp="resp" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import type { HttpStepConfig } from '@/types/apifox'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { useResolvableVarsReload } from '@/composables/useResolvableVars'
import ApiEndpointEditor from '@/components/apifox/endpoint/ApiEndpointEditor.vue'
import DebugResponsePanel from '@/components/apifox/endpoint/DebugResponsePanel.vue'

const props = defineProps<{
  config: HttpStepConfig
  serverNames?: string[]
  projectId: Id
}>()

const store = useWorkspaceStore()
const reloadResolvableVars = useResolvableVarsReload()
const sending = ref(false)
const resp = ref<Schemas['DebugResponse'] | null>(null)

async function send() {
  sending.value = true
  try {
    resp.value = await apifoxApi.debugSend(props.projectId, {
      method: props.config.method,
      path: props.config.path,
      server_name: props.config.server_name,
      request_spec: props.config.request_spec as Schemas['DebugRequest']['request_spec'],
      environment_id: store.currentEnvironmentId,
      assertions: props.config.assertions as Schemas['DebugRequest']['assertions'],
      extracts: props.config.extracts as Schemas['DebugRequest']['extracts'],
    })
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

<style scoped>
.send-hint {
  margin: var(--ax-space-1) 0 0;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}
</style>

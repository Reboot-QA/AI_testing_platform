<template>
  <div class="ai-case-debug">
    <div class="debug-bar">
      <div class="debug-bar-main">
        <MethodTag v-if="ready" :method="form.method" />
        <code v-if="ready" class="debug-path">{{ form.path }}</code>
        <span class="debug-hint">与接口调试相同；环境在顶部选择</span>
      </div>
      <div class="debug-bar-actions">
        <el-button type="success" size="small" :loading="sending" @click="send">
          <el-icon><VideoPlay /></el-icon>
          运行
        </el-button>
        <el-button type="primary" size="small" @click="savePreview">保存</el-button>
      </div>
    </div>

    <ApiEndpointEditor
      v-if="ready"
      :form="form"
      :show-meta="false"
      :show-save="false"
      :server-names="serverNames"
      :project-id="projectId"
      show-processors
      :scripts="scripts"
      :schemas="schemas"
    />

    <DebugResponsePanel v-if="resp" :resp="resp" class="debug-resp" />
    <p v-else class="resp-placeholder">点击「运行」查看返回响应</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { useDebugConsolePrint } from '@/composables/useDebugConsolePrint'
import { useResolvableVarsReload } from '@/composables/useResolvableVars'
import { deriveProcessors, processorsToLegacy } from '@/utils/caseProcessors'
import { emptySpec, normalizeSpec } from '@/utils/apifoxSpec'
import ApiEndpointEditor from '@/components/apifox/endpoint/ApiEndpointEditor.vue'
import DebugResponsePanel from '@/components/apifox/endpoint/DebugResponsePanel.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import type { EndpointEditorForm } from '@/types/apifox'

const model = defineModel<Schemas['CaseCreate']>({ required: true })

const props = defineProps<{
  endpointId: Id
  projectId: Id
}>()

const store = useWorkspaceStore()
const { enabled: consolePrintDbEnabled } = useDebugConsolePrint()
const reloadResolvableVars = useResolvableVarsReload()

const ready = ref(false)
const sending = ref(false)
const resp = ref<Schemas['DebugResponse'] | null>(null)
const scripts = ref<Schemas['ScriptBrief'][]>([])
const schemas = ref<Schemas['SchemaBrief'][]>([])
const serverNames = ref<string[]>([])

const endpoint = ref<Schemas['EndpointOut'] | null>(null)

const form = reactive<EndpointEditorForm>({
  method: 'GET',
  path: '',
  name: '',
  server_name: null,
  request_spec: emptySpec(),
  pre_processors: [],
  post_processors: [],
  assertions: [],
  extracts: [],
  pre_scripts: [],
  post_scripts: [],
})

function applyCaseToForm(c: Schemas['CaseCreate'], ep: Schemas['EndpointOut']) {
  form.method = ep.method
  form.path = ep.path
  form.name = ep.name
  form.server_name = ep.server_name
  form.request_spec = normalizeSpec(c.request_spec ?? ep.request_spec)
  form.pre_processors = [...(c.pre_processors || [])]
  form.post_processors = [...(c.post_processors || [])]
  form.assertions = [...(c.assertions || [])]
  form.extracts = [...(c.extracts || [])]
  form.pre_scripts = []
  form.post_scripts = []
  deriveProcessors(form)
}

function syncFormToModel() {
  model.value = {
    ...model.value,
    request_spec: form.request_spec as Schemas['CaseCreate']['request_spec'],
    pre_processors: [...(form.pre_processors || [])],
    post_processors: [...(form.post_processors || [])],
    assertions: [],
    extracts: [],
    pre_scripts: [],
    post_scripts: [],
  }
}

function savePreview() {
  syncFormToModel()
  ElMessage.success('已保存到生成预览，入库时将使用当前内容')
}

async function send() {
  if (!endpoint.value) return
  syncFormToModel()
  sending.value = true
  try {
    const legacy = processorsToLegacy(form.pre_processors || [], form.post_processors || [])
    resp.value = await apifoxApi.debugSend(props.projectId, {
      method: form.method,
      path: form.path,
      server_name: form.server_name || null,
      request_spec: form.request_spec as Schemas['DebugRequest']['request_spec'],
      environment_id: store.currentEnvironmentId,
      pre_processors: form.pre_processors,
      post_processors: form.post_processors,
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
    if (resp.value.extract_results?.some((r) => r.passed && r.scope !== 'temporary')) {
      await reloadResolvableVars()
    }
  } catch (e: unknown) {
    ElMessage.error(e instanceof Error ? e.message : '运行失败')
  } finally {
    sending.value = false
  }
}

watch(
  () => [form.request_spec, form.pre_processors, form.post_processors] as const,
  () => syncFormToModel(),
  { deep: true },
)

onMounted(async () => {
  const [ep, scriptList, schemaList, envs] = await Promise.all([
    apifoxApi.getEndpoint(props.endpointId),
    apifoxApi.listScripts(props.projectId),
    apifoxApi.listSchemas(props.projectId),
    apifoxApi.listEnvironments(props.projectId),
  ])
  endpoint.value = ep
  scripts.value = scriptList
  schemas.value = schemaList
  const env = envs.find((e) => e.id === store.currentEnvironmentId) ?? envs[0]
  serverNames.value = (env?.servers || []).map((s) => s.name).filter(Boolean) as string[]
  applyCaseToForm(model.value, ep)
  ready.value = true
})
</script>

<style scoped>
.ai-case-debug {
  margin-top: var(--ax-space-2);
  padding-top: var(--ax-space-2);
  border-top: 1px dashed var(--ax-border);
}

.debug-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
}

.debug-bar-main {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--ax-space-2);
  min-width: 0;
  flex: 1;
}

.debug-bar-actions {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  flex-shrink: 0;
  margin-left: auto;
}

.debug-path {
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.debug-hint {
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}

.debug-resp {
  margin-top: var(--ax-space-2);
}

.resp-placeholder {
  margin: var(--ax-space-3) 0 0;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-placeholder);
  text-align: center;
}

.ai-case-debug :deep(.spec-tabs) {
  max-height: 42vh;
  overflow: auto;
}
</style>

<template>
  <div>
    <div class="sd-field">
      <span class="sd-label">引用用例</span>
      <el-select
        v-model="step.ref_case_id"
        filterable
        size="small"
        style="flex: 1"
        @change="onCaseChange"
      >
        <el-option
          v-for="c in cases"
          :key="c.id"
          :label="`[${c.endpoint_method}] ${c.endpoint_name} / ${c.name}`"
          :value="c.id"
        />
      </el-select>
    </div>
    <el-alert
      type="warning"
      :closable="false"
      show-icon
      title="用例为共享：这里的改动会影响所有引用它的场景/接口"
      class="sd-alert"
    />

    <!-- 对齐 Apifox / 接口调试：展示 method + 实际 URL -->
    <div v-if="step.ref_case_id" class="case-url-bar">
      <MethodTag v-if="endpointMeta.method" :method="endpointMeta.method" />
      <span v-if="endpointMeta.server_name" class="case-server">{{
        endpointMeta.server_name
      }}</span>
      <span class="case-path" :title="displayUrl">{{ displayUrl }}</span>
    </div>

    <CaseEditorInline
      v-if="step.ref_case_id"
      ref="inlineRef"
      :case-id="step.ref_case_id"
      :project-id="pid"
      :scripts="scripts"
      :datasets="datasets"
      @saved="onCaseSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouteParamId } from '@/composables/useRouteParamId'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import type { ScenarioEditorStep } from '@/types/apifox'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import CaseEditorInline from '@/components/apifox/case/CaseEditorInline.vue'

type ProjectCaseBrief = Schemas['ProjectCaseBrief']
type ScriptBrief = Schemas['ScriptBrief']
type DatasetBrief = Schemas['DatasetBrief']

const props = withDefaults(
  defineProps<{
    cases?: ProjectCaseBrief[]
    scripts?: ScriptBrief[]
    datasets?: DatasetBrief[]
  }>(),
  {
    cases: () => [],
    scripts: () => [],
    datasets: () => [],
  },
)
const step = defineModel<ScenarioEditorStep>('step', { required: true })

const pid = useRouteParamId()
const workspaceStore = useWorkspaceStore()
const inlineRef = ref<InstanceType<typeof CaseEditorInline> | null>(null)

const endpointMeta = reactive({
  method: '',
  path: '',
  server_name: null as string | null,
})

const displayUrl = computed(() => {
  const path = endpointMeta.path || '/'
  const env = workspaceStore.currentEnvironment
  if (!env) return path
  let base = env.base_url || ''
  if (endpointMeta.server_name) {
    const server = env.servers?.find((s) => s.name === endpointMeta.server_name)
    if (server?.base_url) base = server.base_url
  }
  if (!base) return path
  return base.replace(/\/$/, '') + (path.startsWith('/') ? path : `/${path}`)
})

function clearEndpointMeta() {
  endpointMeta.method = ''
  endpointMeta.path = ''
  endpointMeta.server_name = null
}

async function loadEndpointMeta(endpointId: number, fallbackMethod = '') {
  try {
    const ep = await apifoxApi.getEndpoint(endpointId)
    endpointMeta.method = ep.method
    endpointMeta.path = ep.path
    endpointMeta.server_name = ep.server_name ?? null
    step.value.endpoint_method = ep.method
    step.value.endpoint_path = ep.path
  } catch {
    endpointMeta.method = fallbackMethod || step.value.endpoint_method || ''
    endpointMeta.path = step.value.endpoint_path || ''
    endpointMeta.server_name = null
  }
}

watch(
  () => step.value.ref_case_id,
  (id) => {
    if (!id) {
      clearEndpointMeta()
      return
    }
    const brief = props.cases.find((c) => c.id === id)
    if (brief) {
      endpointMeta.method = brief.endpoint_method
      void loadEndpointMeta(brief.endpoint_id, brief.endpoint_method)
    } else if (step.value.endpoint_path) {
      endpointMeta.method = step.value.endpoint_method || ''
      endpointMeta.path = step.value.endpoint_path
    }
  },
  { immediate: true },
)

function onCaseChange(id: number) {
  const c = props.cases.find((x) => x.id === id)
  if (c) {
    step.value.case_name = c.name
    step.value.endpoint_method = c.endpoint_method
  }
}

function onCaseSaved(_id: Id, name: string) {
  step.value.case_name = name
}

async function flushCase() {
  await inlineRef.value?.flushCase?.()
}

function isCaseDirty(): boolean {
  return inlineRef.value?.isCaseDirty?.() ?? false
}

defineExpose({ flushCase, isCaseDirty })
</script>

<style scoped>
.sd-field {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
}

.sd-label {
  flex-shrink: 0;
  width: 80px;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.sd-alert {
  margin-bottom: var(--ax-space-3);
}

.case-url-bar {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
  padding: var(--ax-space-1-5) var(--ax-space-2);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-sm);
  background: var(--ax-bg-subtle);
}

.case-server {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-tertiary);
}

.case-path {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: Consolas, Monaco, monospace;
  font-size: var(--ax-font-sm);
  color: var(--ax-text);
}
</style>

<template>
  <div class="flex h-full min-h-0 flex-col overflow-hidden">
    <el-tabs v-model="tab" class="mb-1 shrink-0">
      <el-tab-pane label="测试用例" name="cases" />
      <el-tab-pane v-if="!readonly" name="ai-gen">
        <template #label>
          <span class="ai-tab-label">
            AI 生成
            <span v-if="aiGenDot" class="ai-tab-dot" title="有进行中的生成任务" />
          </span>
        </template>
      </el-tab-pane>
      <el-tab-pane label="测试报告" name="reports" />
      <el-tab-pane label="文档" name="doc" />
    </el-tabs>

    <div class="min-h-0 flex-1 overflow-hidden">
      <EndpointCasesTab
        v-show="tab === 'cases'"
        class="h-full"
        :endpoint-id="endpointId"
        :project-id="projectId"
        :readonly="readonly"
        @changed="onCasesChanged"
        @open-ai-gen="(start) => openAiGen(start)"
      />
      <AiGenEndpointPanel
        v-if="!readonly"
        v-show="tab === 'ai-gen'"
        ref="aiPanelRef"
        class="h-full"
        :endpoint-id="endpointId"
        :project-id="projectId"
        @view-cases="tab = 'cases'"
        @applied="emit('cases-changed')"
      />
      <EndpointReportsTab
        v-if="tab === 'reports'"
        class="h-full"
        :endpoint-id="endpointId"
        :project-id="projectId"
      />
      <EndpointDocTab v-else-if="tab === 'doc'" class="h-full" :endpoint-id="endpointId" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { Id } from '@/api/request'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import EndpointCasesTab from '@/components/apifox/endpoint/EndpointCasesTab.vue'
import EndpointReportsTab from '@/components/apifox/endpoint/EndpointReportsTab.vue'
import EndpointDocTab from '@/components/apifox/endpoint/EndpointDocTab.vue'
import AiGenEndpointPanel from '@/components/apifox/ai/AiGenEndpointPanel.vue'

const props = withDefaults(
  defineProps<{
    endpointId: Id
    projectId: Id
    readonly?: boolean
  }>(),
  { readonly: false },
)
const emit = defineEmits<{ 'cases-changed': [] }>()

const tab = ref('cases')
const aiPanelRef = ref<InstanceType<typeof AiGenEndpointPanel> | null>(null)
const aiGenStore = useApifoxAiGenerateStore()

const aiGenDot = computed(() => {
  const t = aiGenStore.latestTaskForEndpoint(Number(props.endpointId))
  return !!t && !['succeeded', 'partial', 'failed', 'canceled'].includes(t.status)
})

async function openAiGen(startDialog?: boolean) {
  tab.value = 'ai-gen'
  if (startDialog) {
    await nextTick()
    aiPanelRef.value?.openStart()
  }
}

function onCasesChanged() {
  void aiPanelRef.value?.refreshCaseCount?.()
  emit('cases-changed')
}

watch(tab, (name) => {
  if (name === 'ai-gen') void aiPanelRef.value?.refreshCaseCount?.()
})

watch(
  () => props.endpointId,
  () => {
    tab.value = 'cases'
  },
)
</script>

<style scoped>
.ai-tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ai-tab-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-blue-6);
}
</style>

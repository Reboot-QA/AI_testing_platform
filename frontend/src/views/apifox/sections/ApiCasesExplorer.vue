<template>
  <div class="flex h-full min-h-0 gap-4">
    <ApiTreePanel
      ref="treeRef"
      :project-id="projectId"
      :case-counts="caseCounts"
      readonly
      @select="onSelectEndpoint"
      @deleted="onDeleted"
      @case-added="loadCounts"
    />
    <ApiCasesPanel
      v-if="selectedEndpointId"
      :endpoint-id="selectedEndpointId"
      :project-id="projectId"
      class="min-w-0 flex-1 overflow-hidden"
      @cases-changed="loadCounts"
    />
    <el-empty
      v-else
      description="选择左侧接口，管理其测试用例"
      class="min-w-0 flex-1 overflow-auto"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import type { Id } from '@/api/request'
import { apifoxApi } from '@/api'
import ApiTreePanel from '@/components/apifox/endpoint/ApiTreePanel.vue'
import ApiCasesPanel from '@/components/apifox/endpoint/ApiCasesPanel.vue'

const props = defineProps<{ projectId: Id }>()

const treeRef = ref<InstanceType<typeof ApiTreePanel> | null>(null)
const selectedEndpointId = ref<number | null>(null)
const caseCounts = ref<Record<number, number>>({})

function onSelectEndpoint(id: number) {
  selectedEndpointId.value = id
  loadCounts()
}
function onDeleted(id: number) {
  if (selectedEndpointId.value === id) selectedEndpointId.value = null
  loadCounts()
}

// 左树接口用例数：按项目下接口聚合（与 listCases 一致，以 endpoint 归属为准）
async function loadCounts() {
  const list = await apifoxApi.listProjectCases(props.projectId)
  const counts: Record<number, number> = {}
  for (const c of list) {
    const eid = Number(c.endpoint_id)
    counts[eid] = (counts[eid] ?? 0) + 1
  }
  caseCounts.value = counts
}

watch(
  () => props.projectId,
  () => {
    selectedEndpointId.value = null
    loadCounts()
  },
)

onMounted(loadCounts)
</script>

<template>
  <div class="h-full min-h-0 overflow-auto">
    <ApiDocPreview v-if="form" :form="form" />
    <el-empty v-else description="加载中…" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Id } from '@/api/request'
import { apifoxApi } from '@/api'
import { normalizeSpec } from '@/utils/apifoxSpec'
import ApiDocPreview from '@/components/apifox/endpoint/ApiDocPreview.vue'
import type { ApiDocPreviewForm } from '@/types/apifox'

const props = defineProps<{ endpointId: Id }>()

const form = ref<ApiDocPreviewForm | null>(null)

async function load() {
  if (!props.endpointId) {
    form.value = null
    return
  }
  const ep = await apifoxApi.getEndpoint(props.endpointId)
  form.value = {
    method: ep.method,
    path: ep.path,
    name: ep.name,
    request_spec: normalizeSpec(ep.request_spec),
  }
}

watch(() => props.endpointId, load, { immediate: true })
</script>

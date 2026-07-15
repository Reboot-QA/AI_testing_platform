<template>
  <div class="doc-tab">
    <ApiDocPreview v-if="form" :form="form" />
    <el-empty v-else description="加载中…" :image-size="60" />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { apifoxApi } from '@/api'
import { normalizeSpec } from '@/utils/apifoxSpec'
import ApiDocPreview from '@/components/apifox/ApiDocPreview.vue'

const props = defineProps({
  endpointId: { type: [String, Number], required: true },
})

const form = ref(null)

async function load() {
  if (!props.endpointId) {
    form.value = null
    return
  }
  const ep = await apifoxApi.getEndpoint(props.endpointId)
  form.value = { method: ep.method, path: ep.path, request_spec: normalizeSpec(ep.request_spec) }
}

watch(() => props.endpointId, load, { immediate: true })
</script>

<style scoped>
.doc-tab {
  overflow: auto;
  height: calc(100vh - 360px);
}
</style>

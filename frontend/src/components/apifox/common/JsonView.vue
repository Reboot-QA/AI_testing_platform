<template>
  <vue-json-pretty
    v-if="isJson"
    :data="parsed"
    :deep="deep"
    :show-length="true"
    :show-line="false"
    :show-icon="true"
  />
  <pre v-else class="raw">{{ text }}</pre>
</template>

<script setup>
import { computed } from 'vue'
import VueJsonPretty from 'vue-json-pretty'
import 'vue-json-pretty/lib/styles.css'

const props = defineProps({
  // 接受已解析对象/数组，或 JSON 字符串（自动解析）
  data: { type: [String, Object, Array, Number, Boolean], default: '' },
  deep: { type: Number, default: 2 },
})

const parsed = computed(() => {
  if (typeof props.data !== 'string') return props.data
  try {
    return JSON.parse(props.data)
  } catch {
    return props.data
  }
})

const isJson = computed(() => parsed.value !== null && typeof parsed.value === 'object')
const text = computed(() => (typeof props.data === 'string' ? props.data : JSON.stringify(props.data)))
</script>

<style scoped>
.raw {
  margin: 0;
  padding: 8px;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--ax-text);
}
</style>

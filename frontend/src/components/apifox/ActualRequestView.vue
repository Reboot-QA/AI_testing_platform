<template>
  <div class="actual-req">
    <div class="req-line">
      <MethodTag v-if="method" :method="method" />
      <span class="url">{{ url || '-' }}</span>
    </div>

    <div class="sec-title">请求头</div>
    <div class="box">
      <JsonView v-if="hasHeaders" :data="headers" :deep="2" />
      <span v-else class="empty">（无请求头）</span>
    </div>

    <div class="sec-title">请求体</div>
    <div class="box">
      <JsonView v-if="hasBody" :data="body" :deep="3" />
      <span v-else class="empty">（无请求体）</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import JsonView from '@/components/apifox/common/JsonView.vue'

// 变量替换/认证注入后实际发出的请求（method/url/headers/body），调试结果与运行报告共用
const props = defineProps({
  method: { type: String, default: '' },
  url: { type: String, default: '' },
  headers: { type: [Object, String], default: () => ({}) },
  body: { type: String, default: '' },
})

const hasHeaders = computed(() => {
  const h = props.headers
  return h && (typeof h === 'string' ? h.length > 0 : Object.keys(h).length > 0)
})
const hasBody = computed(() => !!(props.body && String(props.body).trim()))
</script>

<style scoped>
.req-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  word-break: break-all;
}

.url {
  font-size: 13px;
  color: var(--ax-text-secondary);
}

.sec-title {
  font-weight: 600;
  color: var(--ax-text-tertiary);
  margin: 10px 0 4px;
  font-size: 13px;
}

.box {
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  padding: 8px;
  font-size: 12px;
  max-height: 260px;
  overflow: auto;
}

.empty {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}
</style>

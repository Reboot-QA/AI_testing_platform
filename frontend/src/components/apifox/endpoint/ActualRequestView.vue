<template>
  <div class="actual-req">
    <section class="req-block">
      <header class="req-block__head">请求 URL</header>
      <div class="url-bar">
        <MethodTag v-if="method" :method="method" />
        <span class="url">{{ url || '-' }}</span>
      </div>
    </section>

    <section class="req-block">
      <header class="req-block__head">Header</header>
      <table v-if="headerRows.length" class="hdr-table">
        <thead>
          <tr>
            <th class="hdr-name">名称</th>
            <th>值</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in headerRows" :key="h.name">
            <td class="hdr-name">{{ h.name }}</td>
            <td class="hdr-val">{{ h.value }}</td>
          </tr>
        </tbody>
      </table>
      <span v-else class="empty">（无请求头）</span>
    </section>

    <section class="req-block">
      <header class="req-block__head">
        Body
        <span v-if="contentType" class="ct">{{ contentType }}</span>
      </header>
      <div class="body-box">
        <JsonView v-if="hasBody" :data="body" :deep="4" />
        <span v-else class="empty">（空）</span>
      </div>
    </section>

    <section class="req-block">
      <header class="req-block__head">请求代码</header>
      <RequestCodeGen :method="method" :url="url" :headers="headers" :body="body" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import JsonView from '@/components/apifox/common/JsonView.vue'
import RequestCodeGen from '@/components/apifox/endpoint/RequestCodeGen.vue'

const props = withDefaults(
  defineProps<{
    method?: string
    url?: string
    headers?: Record<string, unknown> | string
    body?: string
  }>(),
  { method: '', url: '', headers: () => ({}), body: '' },
)

const headerRows = computed<{ name: string; value: string }[]>(() => {
  const h = props.headers
  const rows =
    !h || typeof h === 'string'
      ? []
      : Object.entries(h).map(([name, value]) => ({ name, value: String(value ?? '') }))
  // 前置 Host 头：客户端实际发送时自动带，展示上对齐 apifox（7/23-#7）
  let host = ''
  try {
    host = new URL(props.url).host
  } catch {
    host = ''
  }
  if (host && !rows.some((r) => r.name.toLowerCase() === 'host')) {
    rows.unshift({ name: 'Host', value: host })
  }
  return rows
})

const contentType = computed(
  () => headerRows.value.find((r) => r.name.toLowerCase() === 'content-type')?.value || '',
)
const hasBody = computed(() => !!(props.body && String(props.body).trim()))
</script>

<style scoped>
.actual-req {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
}

.req-block__head {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-1-5);
  font-size: var(--ax-font-xs);
  font-weight: 600;
  color: var(--ax-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.ct {
  font-weight: 400;
  color: var(--ax-text-placeholder);
  text-transform: none;
  letter-spacing: normal;
}

.url-bar {
  display: flex;
  align-items: flex-start;
  gap: var(--ax-space-2);
  padding: var(--ax-space-2) var(--ax-space-3);
  border-radius: var(--ax-radius-sm);
  background: color-mix(in srgb, var(--color-purple-6) 5%, var(--ax-bg-subtle));
  border: 1px solid var(--ax-border);
  word-break: break-all;
}

.url {
  font-size: var(--ax-font-sm);
  font-family: Consolas, Monaco, monospace;
  color: var(--ax-text);
  line-height: 1.5;
}

.hdr-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--ax-font-xs);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-sm);
  overflow: hidden;
}

.hdr-table thead {
  background: var(--ax-bg-subtle);
}

.hdr-table th {
  text-align: left;
  padding: var(--ax-space-1-5) var(--ax-space-2);
  color: var(--ax-text-secondary);
  font-weight: 600;
  border-bottom: 1px solid var(--ax-border);
}

.hdr-table td {
  padding: var(--ax-space-1-5) var(--ax-space-2);
  border-bottom: 1px solid color-mix(in srgb, var(--ax-border) 70%, transparent);
  word-break: break-all;
}

.hdr-table tbody tr:last-child td {
  border-bottom: none;
}

.hdr-table tbody tr:nth-child(even) {
  background: color-mix(in srgb, var(--ax-bg-subtle) 60%, var(--ax-bg));
}

.hdr-name {
  width: 200px;
  color: var(--ax-text-secondary);
  font-weight: 500;
}

.hdr-val {
  color: var(--ax-text);
  font-family: Consolas, Monaco, monospace;
}

.body-box {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-sm);
  padding: var(--ax-space-2);
  background: color-mix(in srgb, var(--ax-bg-subtle) 80%, var(--ax-bg));
  max-height: 260px;
  overflow: auto;
  font-size: var(--ax-font-xs);
}

.empty {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-sm);
}
</style>

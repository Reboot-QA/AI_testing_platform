<template>
  <div class="cookie-view">
    <section class="cv-sec">
      <header class="cv-title">请求 Cookie</header>
      <table v-if="reqCookies.length" class="cv-table">
        <thead>
          <tr>
            <th class="cv-name">名称</th>
            <th>值</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in reqCookies" :key="'q' + c.name">
            <td class="cv-name">{{ c.name }}</td>
            <td class="cv-val">{{ c.value }}</td>
          </tr>
        </tbody>
      </table>
      <span v-else class="cv-empty">没有内容</span>
    </section>

    <section class="cv-sec">
      <header class="cv-title">响应 Set-Cookie</header>
      <table v-if="respCookies.length" class="cv-table">
        <thead>
          <tr>
            <th class="cv-name">名称</th>
            <th>值</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in respCookies" :key="'s' + c.name">
            <td class="cv-name">{{ c.name }}</td>
            <td class="cv-val">{{ c.value }}</td>
          </tr>
        </tbody>
      </table>
      <span v-else class="cv-empty">没有内容</span>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    requestHeaders?: Record<string, unknown> | string
    responseHeaders?: Record<string, unknown> | string
  }>(),
  { requestHeaders: () => ({}), responseHeaders: () => ({}) },
)

interface Cookie {
  name: string
  value: string
}

function headerValue(headers: Record<string, unknown> | string | undefined, name: string): string {
  if (!headers || typeof headers === 'string') return ''
  const hit = Object.entries(headers).find(([k]) => k.toLowerCase() === name.toLowerCase())
  return hit ? String(hit[1] ?? '') : ''
}

const reqCookies = computed<Cookie[]>(() => {
  const raw = headerValue(props.requestHeaders, 'cookie')
  if (!raw.trim()) return []
  return raw
    .split(';')
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => {
      const i = p.indexOf('=')
      return i < 0 ? { name: p, value: '' } : { name: p.slice(0, i), value: p.slice(i + 1) }
    })
})

const respCookies = computed<Cookie[]>(() => {
  const raw = headerValue(props.responseHeaders, 'set-cookie')
  if (!raw.trim()) return []
  return raw
    .split(/,\s*(?=[^;,\s]+=)/)
    .map((seg) => seg.split(';')[0].trim())
    .filter(Boolean)
    .map((p) => {
      const i = p.indexOf('=')
      return i < 0 ? { name: p, value: '' } : { name: p.slice(0, i), value: p.slice(i + 1) }
    })
})
</script>

<style scoped>
.cookie-view {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
}

.cv-title {
  margin-bottom: var(--ax-space-1-5);
  font-size: var(--ax-font-xs);
  font-weight: 600;
  color: var(--ax-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.cv-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: var(--ax-font-xs);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-sm);
  overflow: hidden;
}

.cv-table thead {
  background: var(--ax-bg-subtle);
}

.cv-table th {
  text-align: left;
  padding: var(--ax-space-1-5) var(--ax-space-2);
  color: var(--ax-text-secondary);
  font-weight: 600;
  border-bottom: 1px solid var(--ax-border);
}

.cv-table td {
  padding: var(--ax-space-1-5) var(--ax-space-2);
  border-bottom: 1px solid color-mix(in srgb, var(--ax-border) 70%, transparent);
  word-break: break-all;
}

.cv-table tbody tr:last-child td {
  border-bottom: none;
}

.cv-table tbody tr:nth-child(even) {
  background: color-mix(in srgb, var(--ax-bg-subtle) 60%, var(--ax-bg));
}

.cv-name {
  width: 200px;
  color: var(--ax-text-secondary);
  font-weight: 500;
}

.cv-val {
  color: var(--ax-text);
  font-family: Consolas, Monaco, monospace;
}

.cv-empty {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-font-sm);
}
</style>

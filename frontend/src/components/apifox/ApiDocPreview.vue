<template>
  <div class="doc-preview">
    <div class="doc-head">
      <MethodTag :method="form.method" />
      <span class="path">{{ form.path || '/' }}</span>
    </div>
    <div class="doc-name">{{ form.name }}</div>
    <div v-if="form.description" class="doc-desc">{{ form.description }}</div>

    <section v-if="rows(spec.query).length">
      <h4>Query 参数</h4>
      <ParamTable :rows="rows(spec.query)" />
    </section>
    <section v-if="rows(spec.path_params).length">
      <h4>Path 变量</h4>
      <ParamTable :rows="rows(spec.path_params)" />
    </section>
    <section v-if="rows(spec.headers).length">
      <h4>Headers</h4>
      <ParamTable :rows="rows(spec.headers)" />
    </section>
    <section v-if="spec.body && spec.body.type !== 'none'">
      <h4>Body（{{ spec.body.type }}）</h4>
      <JsonView v-if="spec.body.type === 'json'" :data="spec.body.raw" :deep="3" />
      <pre v-else-if="['raw', 'xml'].includes(spec.body.type)" class="raw">{{ spec.body.raw }}</pre>
      <template v-else-if="spec.body.type === 'graphql'">
        <pre class="raw">{{ spec.body.graphql_query }}</pre>
        <pre v-if="spec.body.graphql_variables" class="raw">{{ spec.body.graphql_variables }}</pre>
      </template>
      <div v-else-if="spec.body.type === 'binary'" class="raw">
        {{ spec.body.file_name || '（未选择文件）' }}
      </div>
      <ParamTable v-else :rows="rows(spec.body.form)" />
    </section>
    <section v-if="spec.cookies && rows(spec.cookies).length">
      <h4>Cookies</h4>
      <ParamTable :rows="rows(spec.cookies)" />
    </section>
    <section v-if="spec.auth && spec.auth.type !== 'none'">
      <h4>Auth</h4>
      <div class="auth">类型：{{ spec.auth.type }}</div>
    </section>

    <el-empty v-if="isEmpty" description="该接口暂无请求参数配置" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { computed, h, type VNode } from 'vue'
import { ElTable, ElTableColumn } from 'element-plus'
import type { ApiDocPreviewForm, KvRow, RequestSpec } from '@/types/apifox'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import JsonView from '@/components/apifox/common/JsonView.vue'

const props = defineProps<{ form: ApiDocPreviewForm }>()

const spec = computed(() => props.form.request_spec || ({} as RequestSpec))

function rows(list: KvRow[] | undefined) {
  return (list || []).filter((r) => r && r.enabled !== false && (r.key || '').trim())
}

const isEmpty = computed(() => {
  const s = spec.value
  return (
    !rows(s.query).length &&
    !rows(s.path_params).length &&
    !rows(s.headers).length &&
    (!s.body || s.body.type === 'none') &&
    (!s.auth || s.auth.type === 'none')
  )
})

// 只读参数小表（内联函数式组件，避免额外文件）
const ParamTable = (p: { rows: KvRow[] }): VNode =>
  h(ElTable, { data: p.rows, size: 'small', border: true }, () => [
    h(ElTableColumn, { prop: 'key', label: '参数名', width: 220 }),
    h(ElTableColumn, { prop: 'value', label: '值' }),
    h(ElTableColumn, { prop: 'desc', label: '说明' }),
  ])
</script>

<style scoped>
.doc-preview {
  padding: 4px 2px;
}

.doc-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.path {
  font-family: Consolas, Monaco, monospace;
  color: var(--ax-text);
}

.doc-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--ax-brand);
  margin: 8px 0 4px;
}

.doc-desc {
  color: var(--ax-text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}

section {
  margin-top: 14px;
}

h4 {
  margin: 0 0 6px;
  font-size: 13px;
  color: var(--ax-text-tertiary);
}

.raw {
  margin: 0;
  padding: 8px;
  background: var(--ax-bg-subtle);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

.auth {
  font-size: 13px;
  color: var(--ax-text);
}
</style>

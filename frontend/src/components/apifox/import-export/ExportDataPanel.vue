<template>
  <div class="io-page">
    <header class="io-head">
      <div>
        <h2 class="io-title">导出数据</h2>
        <p class="io-desc">选择导出格式与范围，生成可下载的数据文件</p>
      </div>
      <el-button @click="apiAccessOpen = true">
        通过 API 导出
        <el-icon class="io-ext"><Link /></el-icon>
      </el-button>
    </header>
    <ApiAccessDialog v-model="apiAccessOpen" mode="export" />

    <section class="io-section">
      <h3 class="io-section-title">选择格式</h3>
      <div class="io-cards io-cards--6">
        <button
          v-for="f in FORMATS"
          :key="f.key"
          type="button"
          class="io-card"
          :class="{ active: format === f.key }"
          @click="format = f.key"
        >
          <span class="io-card-logo" :class="`tone-${f.tone}`">{{ f.abbr }}</span>
          <span class="io-card-name">{{ f.label }}</span>
        </button>
      </div>
    </section>

    <section class="io-section io-panel">
      <h3 class="io-section-title">导出范围</h3>
      <div class="ed-scope">
        <div class="ed-row">
          <span class="ed-lbl">模块</span>
          <el-select v-model="moduleId" class="ed-module">
            <el-option label="默认模块" value="default" />
          </el-select>
        </div>
        <el-radio-group v-model="scope" class="ed-radios">
          <el-radio value="all">导出全部</el-radio>
          <el-radio value="partial">导出部分接口</el-radio>
          <el-radio value="tags">通过标签筛选</el-radio>
        </el-radio-group>
        <div v-if="scope === 'partial'" class="ed-row">
          <span class="ed-lbl">选择接口</span>
          <el-select
            v-model="selectedEndpoints"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="选择要导出的接口"
            style="flex: 1"
          >
            <el-option
              v-for="e in endpoints"
              :key="e.id"
              :label="`${e.method} ${e.name}`"
              :value="e.id"
            />
          </el-select>
        </div>
        <div v-if="scope === 'tags'" class="ed-row">
          <span class="ed-lbl">包含标签</span>
          <el-input
            v-model="includeTags"
            :maxlength="VALUE_MAX_LEN"
            placeholder="多个标签(文件夹名)用逗号分隔"
            clearable
          />
        </div>
        <div class="ed-row">
          <span class="ed-lbl">排除标签</span>
          <el-input
            v-model="excludeTags"
            :maxlength="VALUE_MAX_LEN"
            placeholder="多个标签用逗号分隔"
            clearable
          />
        </div>
      </div>

      <template v-if="format === 'openapi'">
        <h3 class="io-section-title ed-sub">OpenAPI 选项</h3>
        <div class="ed-scope">
          <div class="ed-row ed-row--top">
            <span class="ed-lbl">版本</span>
            <el-radio-group v-model="openapiVersion">
              <el-radio value="3.1">OpenAPI 3.1</el-radio>
              <el-radio value="3.0">OpenAPI 3.0</el-radio>
              <el-radio value="2.0">Swagger 2.0</el-radio>
            </el-radio-group>
          </div>
          <div class="ed-row ed-row--top">
            <span class="ed-lbl">文件格式</span>
            <el-radio-group v-model="fileFormat">
              <el-radio value="json">JSON</el-radio>
              <el-radio value="yaml">YAML</el-radio>
            </el-radio-group>
          </div>
        </div>
      </template>

      <div class="io-footer">
        <el-button type="primary" :loading="exporting" @click="doExport">导出</el-button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { VALUE_MAX_LEN } from '@/constants/limits'
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useRouteParamId } from '@/composables/useRouteParamId'
import ApiAccessDialog from '@/components/apifox/endpoint/ApiAccessDialog.vue'

type ExportFormat = 'openapi' | 'html' | 'markdown' | 'word' | 'apifox' | 'postman'
type ExportScope = 'all' | 'partial' | 'tags'

const FORMATS: { key: ExportFormat; label: string; abbr: string; tone: string }[] = [
  { key: 'openapi', label: 'OpenAPI Spec', abbr: 'OA', tone: 'green' },
  { key: 'html', label: 'HTML', abbr: 'HT', tone: 'orange' },
  { key: 'markdown', label: 'Markdown', abbr: 'MD', tone: 'slate' },
  { key: 'word', label: 'Word', abbr: 'WD', tone: 'blue' },
  { key: 'apifox', label: 'Apifox', abbr: 'AF', tone: 'brand' },
  { key: 'postman', label: 'Postman', abbr: 'PM', tone: 'orange' },
]

const format = ref<ExportFormat>('openapi')
const moduleId = ref('default')
const scope = ref<ExportScope>('all')
const includeTags = ref('')
const excludeTags = ref('')
const openapiVersion = ref<'3.1' | '3.0' | '2.0'>('3.0')
const fileFormat = ref<'json' | 'yaml'>('json')

const pid = useRouteParamId()
const exporting = ref(false)
const apiAccessOpen = ref(false)
const endpoints = ref<Schemas['EndpointBrief'][]>([])
const selectedEndpoints = ref<number[]>([])

onMounted(async () => {
  try {
    endpoints.value = await apifoxApi.listEndpoints(pid.value)
  } catch {
    /* 忽略 */
  }
})

function comingSoon() {
  ElMessage.info('敬请期待')
}

function download(blob: Blob, filename: string) {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  URL.revokeObjectURL(link.href)
}

function scopeParams(): Record<string, string> {
  const params: Record<string, string> = {
    scope: scope.value === 'partial' ? 'endpoints' : scope.value,
    exclude_tags: excludeTags.value.trim(),
  }
  if (scope.value === 'tags') params.tags = includeTags.value.trim()
  if (scope.value === 'partial') params.endpoint_ids = selectedEndpoints.value.join(',')
  return params
}

const DOC_EXT: Record<string, string> = { html: 'html', markdown: 'md', word: 'docx' }

async function runExport(): Promise<{ blob: Blob; filename: string }> {
  const params = scopeParams()
  if (format.value === 'openapi') {
    params.spec_version = openapiVersion.value === '2.0' ? 'swagger2' : openapiVersion.value
    params.file_format = fileFormat.value
    const ext = fileFormat.value === 'yaml' ? 'yaml' : 'json'
    return {
      blob: await apifoxApi.exportOpenapi(pid.value, params),
      filename: `openapi-project-${pid.value}.${ext}`,
    }
  }
  if (format.value === 'postman') {
    return {
      blob: await apifoxApi.exportPostman(pid.value, params),
      filename: `postman-project-${pid.value}.json`,
    }
  }
  // html / markdown / word → 接口文档
  params.doc_format =
    format.value === 'markdown' ? 'markdown' : format.value === 'word' ? 'word' : 'html'
  const ext = DOC_EXT[params.doc_format] ?? 'html'
  return {
    blob: await apifoxApi.exportDoc(pid.value, params),
    filename: `api-doc-project-${pid.value}.${ext}`,
  }
}

async function doExport() {
  // Apifox 专有格式暂无导出后端，其余（OpenAPI/Postman/HTML/MD/Word）已支持
  if (format.value === 'apifox') {
    comingSoon()
    return
  }
  exporting.value = true
  try {
    const { blob, filename } = await runExport()
    download(blob, filename)
    ElMessage.success('已导出')
  } catch {
    ElMessage.error('导出失败，请重试')
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.io-page {
  max-width: 880px;
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-5);
}

.io-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--ax-space-3);
}

.io-title {
  margin: 0 0 var(--ax-space-1);
  font-size: var(--ax-text-title-size);
  font-weight: 600;
  line-height: var(--ax-leading-tight);
  color: var(--ax-text);
}

.io-desc {
  margin: 0;
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
}

.io-ext {
  margin-left: var(--ax-space-1);
}

.io-section-title {
  margin: 0 0 var(--ax-space-3);
  font-size: var(--ax-text-body-size);
  font-weight: 600;
  color: var(--ax-text);
}

.io-cards {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--ax-space-2-5);
}

.io-cards--6 {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.io-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--ax-space-2);
  padding: var(--ax-space-3) var(--ax-space-2);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg);
  cursor: pointer;
  transition:
    border-color var(--ax-transition),
    background var(--ax-transition);
}

.io-card:hover {
  border-color: var(--ax-brand);
}

.io-card.active {
  border-color: var(--ax-brand);
  background: var(--ax-tag-blue-bg);
}

.io-card-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--ax-radius-sm);
  font-size: var(--ax-font-xs);
  font-weight: 700;
  color: var(--ax-bg);
}

.tone-green {
  background: var(--ax-success);
}
.tone-orange {
  background: var(--ax-warning);
}
.tone-slate {
  background: var(--ax-info);
}
.tone-blue {
  background: var(--ax-brand);
}
.tone-brand {
  background: var(--ax-brand);
}

.io-card-name {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text);
  text-align: center;
}

.io-panel {
  padding: var(--ax-space-4);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
}

.ed-sub {
  margin-top: var(--ax-space-5);
}

.ed-scope {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
}

.ed-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-3);
}

.ed-row--top {
  align-items: flex-start;
}

.ed-lbl {
  flex: none;
  width: 88px;
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-secondary);
  line-height: var(--ax-control-height-sm);
}

.ed-module {
  width: 220px;
}

.ed-radios {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ax-space-2) var(--ax-space-4);
  padding-left: 88px;
}

.io-footer {
  margin-top: var(--ax-space-5);
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 800px) {
  .io-cards,
  .io-cards--6 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>

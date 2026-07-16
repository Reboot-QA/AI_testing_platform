<template>
  <el-dialog
    v-model="visible"
    title="AI 生成接口测试用例"
    width="640px"
    :close-on-click-modal="false"
    @closed="reset"
  >
    <div v-if="step === 'config'" class="config">
      <div class="tip">勾选类别与数量，AI 将按接口定义生成用例供你确认后创建。</div>
      <div class="provider-row">
        <span class="provider-label">大模型</span>
        <el-select
          v-model="providerId"
          size="small"
          :loading="providersLoading"
          :disabled="!llmProviders.length"
          placeholder="选择大模型"
          style="flex: 1"
        >
          <el-option
            v-for="p in llmProviders"
            :key="p.id"
            :label="formatProviderLabel(p)"
            :value="p.id"
          />
        </el-select>
      </div>
      <div v-if="mockMode" class="tip mock-tip">
        当前为 Mock 模式，将返回样例用例（不调用真实模型）。
      </div>
      <div v-for="c in categories" :key="c.value" class="cat-row">
        <el-checkbox v-model="c.checked" class="cat-check">{{ c.label }}</el-checkbox>
        <el-input-number
          v-model="c.count"
          :disabled="!c.checked"
          :min="1"
          :max="20"
          size="small"
          controls-position="right"
          style="width: 110px"
        />
        <span class="cat-desc">{{ c.desc }}</span>
      </div>
    </div>

    <div v-else class="preview">
      <div class="tip">
        共生成 {{ generated.length }} 条<span v-if="mode === 'mock'">（Mock 模式 · 样例数据）</span
        >，勾选要创建的用例：
      </div>
      <el-checkbox
        v-model="allSelected"
        :indeterminate="someSelected"
        class="select-all"
        @change="toggleAll"
        >全选</el-checkbox
      >
      <div v-for="(g, i) in generated" :key="i" class="gen-item">
        <el-checkbox v-model="selected[i]" />
        <el-tag size="small" :type="tagType(g.category)">{{ categoryLabel(g.category) }}</el-tag>
        <div class="gen-body">
          <div class="gen-name">{{ g.name }}</div>
          <div class="gen-sum">{{ summarize(g) }}</div>
        </div>
      </div>
      <el-empty v-if="!generated.length" description="未生成用例" :image-size="50" />
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button v-if="step === 'preview'" :disabled="creating" @click="step = 'config'"
        >上一步</el-button
      >
      <el-button
        v-if="step === 'config'"
        type="primary"
        :loading="loading"
        :disabled="!anyChecked"
        @click="generate"
        >生成</el-button
      >
      <el-button
        v-else
        type="primary"
        :loading="creating"
        :disabled="!selectedCount"
        @click="createSelected"
        >创建勾选（{{ selectedCount }}）</el-button
      >
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apifoxApi, settingsApi } from '@/api'
import { categoryLabel } from '@/utils/caseCategory'

const props = defineProps({
  endpointId: { type: [String, Number], required: true },
})
const emit = defineEmits(['created'])

const DEFAULT_CATEGORIES = () => [
  { value: 'positive', label: '正向', desc: '合法输入，预期成功', checked: true, count: 1 },
  { value: 'negative', label: '逆向', desc: '非法/缺失输入，预期报错', checked: true, count: 2 },
  { value: 'boundary', label: '边界值', desc: '空/零/超长/临界', checked: true, count: 2 },
  { value: 'security', label: '安全性', desc: '注入/越权/异常字符', checked: false, count: 1 },
]

const visible = ref(false)
const step = ref('config')
const loading = ref(false)
const creating = ref(false)
const categories = ref(DEFAULT_CATEGORIES())
const generated = ref([])
const selected = ref([])
const mode = ref('llm')
const llmProviders = ref([])
const providersLoading = ref(false)
const providerId = ref(null)
const mockMode = ref(false)

const anyChecked = computed(() => categories.value.some((c) => c.checked))
const selectedCount = computed(() => selected.value.filter(Boolean).length)
const allSelected = computed(
  () => generated.value.length > 0 && selectedCount.value === generated.value.length,
)
const someSelected = computed(() => selectedCount.value > 0 && !allSelected.value)

const tagType = (cat) =>
  ({ positive: 'success', negative: 'warning', boundary: '', security: 'danger' })[cat] || 'info'

function open() {
  reset()
  visible.value = true
  loadProviders()
}
defineExpose({ open })

function formatProviderLabel(item) {
  const tags = []
  if (item.is_default) tags.push('默认')
  if (!item.api_key_configured) tags.push('未配置Key')
  const suffix = tags.length ? ` (${tags.join(' / ')})` : ''
  return `${item.name}${suffix}`
}

async function loadProviders() {
  providersLoading.value = true
  try {
    const data = await settingsApi.getLLMOptions()
    llmProviders.value = data.providers || []
    mockMode.value = data.mock_mode
    if (data.active_provider_id) {
      providerId.value = data.active_provider_id
    } else if (llmProviders.value.length) {
      providerId.value = llmProviders.value[0].id
    }
  } finally {
    providersLoading.value = false
  }
}

function reset() {
  step.value = 'config'
  categories.value = DEFAULT_CATEGORIES()
  generated.value = []
  selected.value = []
  loading.value = false
  creating.value = false
}

function toggleAll(val) {
  selected.value = generated.value.map(() => !!val)
}

// 断言摘要：把每条断言渲染成「状态码 = 200」这类可读短语，帮用户在预览时判断用例意图
function summarize(g) {
  const rows = (g.assertions || []).filter((a) => a.enabled !== false)
  if (!rows.length) return '无断言'
  return rows
    .slice(0, 3)
    .map((a) => {
      const target = a.type === 'status_code' ? '状态码' : a.path || a.type
      return `${target} ${a.operator} ${a.expected ?? ''}`.trim()
    })
    .join(' · ')
}

async function generate() {
  const payload = {
    categories: categories.value
      .filter((c) => c.checked)
      .map((c) => ({ category: c.value, count: c.count })),
    provider_id: providerId.value ?? undefined,
  }
  loading.value = true
  try {
    const res = await apifoxApi.aiGenerateCases(props.endpointId, payload)
    generated.value = res.cases || []
    selected.value = generated.value.map(() => true)
    mode.value = res.mode
    step.value = 'preview'
  } catch (e) {
    ElMessage.error(e.message || 'AI 生成失败')
  } finally {
    loading.value = false
  }
}

async function createSelected() {
  creating.value = true
  let ok = 0
  const failed = [] // 保留创建失败的条目，供用户重试；成功的从列表移除以防重复创建
  const failedNames = []
  try {
    for (let i = 0; i < generated.value.length; i += 1) {
      if (!selected.value[i]) {
        failed.push(generated.value[i]) // 未勾选的原样保留
        continue
      }
      try {
        await apifoxApi.createCase(props.endpointId, generated.value[i])
        ok += 1
      } catch {
        failed.push(generated.value[i])
        failedNames.push(generated.value[i].name)
      }
    }
  } finally {
    creating.value = false
  }
  generated.value = failed
  selected.value = failed.map(() => true)
  if (ok) emit('created')
  if (failedNames.length) {
    ElMessage.warning(`已创建 ${ok} 条，${failedNames.length} 条失败：${failedNames.join('、')}`)
  } else {
    ElMessage.success(`已创建 ${ok} 条用例`)
    visible.value = false
  }
}
</script>

<style scoped>
.tip {
  color: var(--ax-text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}

.provider-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.provider-label {
  width: 72px;
  font-size: 14px;
}

.mock-tip {
  color: var(--ax-warning, #e6a23c);
}

.cat-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.cat-check {
  width: 72px;
}

.cat-desc {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}

.preview {
  max-height: 52vh;
  overflow: auto;
}

.select-all {
  margin-bottom: 8px;
}

.gen-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  margin-bottom: 6px;
}

.gen-body {
  min-width: 0;
  flex: 1;
}

.gen-name {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gen-sum {
  color: var(--ax-text-placeholder);
  font-size: 12px;
  margin-top: 2px;
}
</style>

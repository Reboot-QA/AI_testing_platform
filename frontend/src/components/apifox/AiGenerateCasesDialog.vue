<template>
  <el-dialog
    v-model="visible"
    title="AI 生成接口测试用例"
    width="640px"
    :close-on-click-modal="false"
    @closed="onClosed"
  >
    <!-- 配置 -->
    <div v-if="step === 'config'" class="config">
      <div class="tip">
        勾选类别，AI
        将按接口复杂度自动决定用例数量；需要时可勾「限量」指定每类上限。生成在后台进行，可关闭弹窗做其他事。
      </div>
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
        <el-checkbox v-model="c.limit" :disabled="!c.checked" size="small">限量</el-checkbox>
        <el-input-number
          v-if="c.limit"
          v-model="c.count"
          :disabled="!c.checked"
          :min="1"
          :max="20"
          size="small"
          controls-position="right"
          style="width: 100px"
        />
        <span v-else class="auto-hint">自动</span>
        <span class="cat-desc">{{ c.desc }}</span>
      </div>
    </div>

    <!-- 生成中 / 结果 -->
    <div v-else class="result">
      <div v-if="generating" class="running">
        <el-progress :percentage="100" :indeterminate="true" :show-text="false" :stroke-width="4" />
        <div class="run-text">AI 生成中，请稍候…（可关闭弹窗，后台继续；完成后重新打开查看）</div>
      </div>
      <el-alert
        v-else-if="item && item.status === 'failed'"
        type="error"
        :closable="false"
        :title="item.error || '生成失败'"
      />
      <template v-else>
        <div class="tip">
          共生成 {{ generated.length }} 条<span v-if="task && task.mode === 'mock'"
            >（Mock 模式 · 样例数据）</span
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
      </template>
    </div>

    <template #footer>
      <template v-if="step === 'config'">
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" :disabled="!anyChecked" @click="generate"
          >生成</el-button
        >
      </template>
      <template v-else-if="generating">
        <el-button @click="visible = false">关闭（后台继续）</el-button>
        <el-button :loading="canceling" @click="cancel">取消生成</el-button>
      </template>
      <template v-else-if="item && item.status === 'failed'">
        <el-button type="primary" @click="backToConfig">返回重试</el-button>
      </template>
      <template v-else>
        <el-button @click="backToConfig">重新生成</el-button>
        <el-button
          type="primary"
          :loading="creating"
          :disabled="!selectedCount"
          @click="createSelected"
          >创建勾选（{{ selectedCount }}）</el-button
        >
      </template>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { settingsApi } from '@/api'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import { categoryLabel } from '@/utils/caseCategory'

const props = defineProps<{
  endpointId: Id
  projectId: Id
}>()
const emit = defineEmits<{ created: [] }>()

const store = useApifoxAiGenerateStore()

interface AiCategoryOption {
  value: string
  label: string
  desc: string
  checked: boolean
  limit: boolean
  count: number
}

const DEFAULT_CATEGORIES = (): AiCategoryOption[] => [
  {
    value: 'positive',
    label: '正向',
    desc: '合法输入，预期成功',
    checked: true,
    limit: false,
    count: 3,
  },
  {
    value: 'negative',
    label: '逆向',
    desc: '非法/缺失输入，预期报错',
    checked: true,
    limit: false,
    count: 3,
  },
  {
    value: 'boundary',
    label: '边界值',
    desc: '空/零/超长/临界',
    checked: true,
    limit: false,
    count: 3,
  },
  {
    value: 'security',
    label: '安全性',
    desc: '注入/越权/异常字符',
    checked: false,
    limit: false,
    count: 2,
  },
]

const visible = ref(false)
const step = ref<'config' | 'result'>('config')
const submitting = ref(false)
const creating = ref(false)
const canceling = ref(false)
const categories = ref<AiCategoryOption[]>(DEFAULT_CATEGORIES())
const selected = ref<boolean[]>([])
const taskId = ref<number | null>(null)
const llmProviders = ref<Schemas['LLMProviderOut'][]>([])
const providersLoading = ref(false)
const providerId = ref<number | null>(null)
const mockMode = ref(false)

const eid = computed(() => Number(props.endpointId))
const task = computed(() => (taskId.value ? store.taskById(taskId.value) : undefined))
const item = computed(() => task.value?.items?.[0])
const generating = computed(
  () => !!task.value && !['succeeded', 'partial', 'failed', 'canceled'].includes(task.value.status),
)
const generated = computed(() => item.value?.cases || [])

const anyChecked = computed(() => categories.value.some((c) => c.checked))
const selectedCount = computed(() => selected.value.filter(Boolean).length)
const allSelected = computed(
  () => generated.value.length > 0 && selectedCount.value === generated.value.length,
)
const someSelected = computed(() => selectedCount.value > 0 && !allSelected.value)

const tagType = (cat: string) =>
  ({ positive: 'success', negative: 'warning', boundary: '', security: 'danger' })[cat] || 'info'

// 生成完成、拿到用例后默认全选
watch(generated, (rows) => {
  if (rows.length && selected.value.length !== rows.length) selected.value = rows.map(() => true)
})

function open() {
  step.value = 'config'
  categories.value = DEFAULT_CATEGORIES()
  selected.value = []
  submitting.value = false
  creating.value = false
  canceling.value = false
  loadProviders()
  // 重开时恢复该接口最近的任务（进行中或本会话刚生成完的），失败的则回配置重试
  const existing = store.latestTaskForEndpoint(eid.value)
  if (existing && existing.status !== 'failed' && existing.status !== 'canceled') {
    taskId.value = existing.id
    step.value = 'result'
  } else {
    taskId.value = null
  }
  visible.value = true
}
defineExpose({ open })

function onClosed() {
  // 关闭不取消任务（后台继续）；仅重置弹窗自身瞬态
  step.value = 'config'
}

function backToConfig() {
  taskId.value = null
  selected.value = []
  step.value = 'config'
}

function formatProviderLabel(item: Schemas['LLMProviderOut']) {
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
    if (data.active_provider_id) providerId.value = data.active_provider_id
    else if (llmProviders.value.length) providerId.value = llmProviders.value[0].id
  } finally {
    providersLoading.value = false
  }
}

function toggleAll(val: boolean) {
  selected.value = generated.value.map(() => !!val)
}

// 断言摘要：把每条断言渲染成「状态码 = 200」这类可读短语，帮用户在预览时判断用例意图
function summarize(g: Schemas['CaseCreate']) {
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
  const cats = categories.value
    .filter((c) => c.checked)
    .map((c) => ({ category: c.value, count: c.limit ? c.count : undefined }))
  submitting.value = true
  try {
    taskId.value = await store.start(Number(props.projectId), [eid.value], cats, providerId.value)
    selected.value = []
    step.value = 'result'
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || 'AI 生成任务创建失败')
  } finally {
    submitting.value = false
  }
}

async function cancel() {
  canceling.value = true
  try {
    await store.cancel(taskId.value)
    ElMessage.info('已取消生成')
    backToConfig()
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '取消失败')
  } finally {
    canceling.value = false
  }
}

async function createSelected() {
  if (!item.value) return
  const indexes = generated.value.map((_, i) => i).filter((i) => selected.value[i])
  creating.value = true
  try {
    const res = await store.applyItem(taskId.value, item.value.id, indexes)
    if (res.created) emit('created')
    if (res.failed?.length) {
      ElMessage.warning(
        `已创建 ${res.created} 条，${res.failed.length} 条失败：${res.failed.join('、')}`,
      )
    } else {
      ElMessage.success(`已创建 ${res.created} 条用例`)
      store.removeTask(taskId.value) // 全部入库成功，移除任务避免重开时重复入库
      taskId.value = null
      visible.value = false
    }
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '入库失败')
  } finally {
    creating.value = false
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

.auto-hint {
  width: 100px;
  font-size: 13px;
  color: var(--ax-text-placeholder);
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

.result {
  max-height: 52vh;
  overflow: auto;
}

.running {
  padding: 24px 8px;
}

.run-text {
  margin-top: 12px;
  color: var(--ax-text-secondary);
  font-size: 13px;
  text-align: center;
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

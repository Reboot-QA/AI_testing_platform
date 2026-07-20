<template>
  <el-dialog
    v-model="visible"
    title="AI 生成接口测试用例"
    width="640px"
    :close-on-click-modal="false"
  >
    <div class="config">
      <div class="tip">
        勾选类别，AI
        将按接口复杂度自动决定用例数量；需要时可勾「限量」指定每类上限。提交后在后台生成，进度与结果请到「AI
        生成」标签页查看。
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

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" :disabled="!anyChecked" @click="generate"
        >生成</el-button
      >
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { settingsApi } from '@/api'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'

const props = defineProps<{
  endpointId: Id
  projectId: Id
}>()

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
const submitting = ref(false)
const categories = ref<AiCategoryOption[]>(DEFAULT_CATEGORIES())
const llmProviders = ref<Schemas['LLMProviderOptionOut'][]>([])
const providersLoading = ref(false)
const providerId = ref<number | null>(null)
const mockMode = ref(false)

const anyChecked = computed(() => categories.value.some((c) => c.checked))

function open() {
  categories.value = DEFAULT_CATEGORIES()
  submitting.value = false
  loadProviders()
  visible.value = true
}
defineExpose({ open })

function formatProviderLabel(item: Schemas['LLMProviderOptionOut']) {
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

async function generate() {
  type AiCategory = Schemas['AiGenTaskCreate']['categories'][number]
  const cats: AiCategory[] = categories.value
    .filter((c) => c.checked)
    .map((c) => ({
      category: c.value as AiCategory['category'],
      count: c.limit ? c.count : undefined,
    }))
  submitting.value = true
  try {
    await store.start(Number(props.projectId), [Number(props.endpointId)], cats, providerId.value)
    ElMessage.success('已提交生成，请到「AI 生成」标签页查看进度与结果')
    visible.value = false
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || 'AI 生成任务创建失败')
  } finally {
    submitting.value = false
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
</style>

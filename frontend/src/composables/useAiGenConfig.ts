import { computed, ref } from 'vue'
import { settingsApi } from '@/api'
import type { Schemas } from '@/api/types'

type ProviderOption = Schemas['LLMProviderOptionOut']
type Category = Schemas['AiGenTaskCreate']['categories'][number]
export type CategoryRow = {
  value: string
  label: string
  desc: string
  checked: boolean
  limit: boolean
  count: number
}

const makeCategories = (): CategoryRow[] => [
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

// AI 生成的公共配置：类别勾选（自动/限量）+ 大模型 Provider 选择 + 生成参数构造。
// 单接口弹窗与批量弹窗共用，避免两处复制。
export function useAiGenConfig() {
  const categories = ref<CategoryRow[]>(makeCategories())
  const llmProviders = ref<ProviderOption[]>([])
  const providersLoading = ref(false)
  const providerId = ref<number | null>(null)
  const mockMode = ref(false)

  const anyChecked = computed(() => categories.value.some((c) => c.checked))

  function resetCategories(): void {
    categories.value = makeCategories()
  }

  async function loadProviders(): Promise<void> {
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

  // 仅勾选的类别；限量则带 count，否则 count=undefined 交后端按接口复杂度自动决定
  function buildCategoriesPayload(): Category[] {
    return categories.value
      .filter((c) => c.checked)
      .map((c) => ({
        category: c.value as Category['category'],
        count: c.limit ? c.count : undefined,
      }))
  }

  return {
    categories,
    llmProviders,
    providersLoading,
    providerId,
    mockMode,
    anyChecked,
    resetCategories,
    loadProviders,
    buildCategoriesPayload,
  }
}

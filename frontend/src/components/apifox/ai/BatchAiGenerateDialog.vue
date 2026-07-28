<template>
  <el-dialog
    v-model="visible"
    title="批量 AI 生成接口测试用例"
    width="720px"
    :close-on-click-modal="false"
  >
    <div class="config">
      <div class="tip">
        选择接口并勾选类别，AI
        按各接口复杂度批量生成用例；已存在的同名用例不会重复创建。默认勾选「无用例」与「待复核」的接口，也可自行选择任意接口。
      </div>
      <AiGenConfigFields
        v-model="providerId"
        :providers="llmProviders"
        :providers-loading="providersLoading"
        :mock-mode="mockMode"
        :categories="categories"
      />
      <div class="ep-block">
        <div class="ep-head">
          <span>接口（{{ checked.length }}/{{ endpoints.length }}）</span>
          <div class="ep-head-right">
            <el-checkbox v-model="onlyNeed" @change="onOnlyNeedChange">只看需生成</el-checkbox>
            <el-checkbox
              :model-value="allEpSelected"
              :indeterminate="someEpSelected"
              @change="toggleAllEndpoints"
              >全选</el-checkbox
            >
          </div>
        </div>
        <el-input
          v-model="epKeyword"
          :maxlength="SEARCH_MAX_LEN"
          size="small"
          placeholder="搜索接口名 / 路径"
          clearable
        />
        <div v-loading="endpointsLoading" class="ep-list">
          <el-checkbox-group v-model="checked">
            <div v-for="ep in filteredEndpoints" :key="ep.id" class="ep-row">
              <el-checkbox :value="ep.id">
                <MethodTag :method="ep.method" />
                <span class="ep-name">{{ ep.name }}</span>
                <span class="ep-path">{{ ep.path }}</span>
                <el-tag v-if="caseCount(ep.id) === 0" size="small" type="info" class="ep-flag"
                  >无用例</el-tag
                >
                <el-tag v-else-if="ep.cases_stale" size="small" type="warning" class="ep-flag"
                  >待复核</el-tag
                >
              </el-checkbox>
            </div>
          </el-checkbox-group>
          <el-empty v-if="!filteredEndpoints.length" description="无接口" :image-size="40" />
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        :disabled="!anyChecked || !checked.length"
        @click="generate"
        >生成（{{ checked.length }} 个接口）</el-button
      >
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { SEARCH_MAX_LEN } from '@/constants/limits'
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useAiGenConfig } from '@/composables/useAiGenConfig'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import AiGenConfigFields from '@/components/apifox/ai/AiGenConfigFields.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

const props = defineProps<{ projectId: string | number }>()
const emit = defineEmits<{ created: [] }>()

type Endpoint = Schemas['EndpointBrief']

const store = useApifoxAiGenerateStore()
const {
  categories,
  llmProviders,
  providersLoading,
  providerId,
  mockMode,
  anyChecked,
  resetCategories,
  loadProviders,
  buildCategoriesPayload,
} = useAiGenConfig()

const visible = ref(false)
const submitting = ref(false)
const endpoints = ref<Endpoint[]>([])
const endpointsLoading = ref(false)
const epKeyword = ref('')
const checked = ref<number[]>([])
const caseCounts = ref<Record<number, number>>({})
const onlyNeed = ref(false)
// 无预选（从 AI 任务中心/批量入口打开）时，加载完默认勾选「需生成」的接口
const autoSelectNeed = ref(false)

const caseCount = (id: number) => caseCounts.value[id] ?? 0
// 需生成：没有用例（新增接口）或受 Swagger 更新影响待复核
const needsGen = (ep: Endpoint) => caseCount(ep.id) === 0 || !!ep.cases_stale

const filteredEndpoints = computed<Endpoint[]>(() => {
  const kw = epKeyword.value.trim().toLowerCase()
  return endpoints.value.filter(
    (e) =>
      (!kw || e.name.toLowerCase().includes(kw) || e.path.toLowerCase().includes(kw)) &&
      (!onlyNeed.value || needsGen(e)),
  )
})

function onOnlyNeedChange() {
  // 切到「只看需生成」时把不在列表里的已勾选清掉，保持勾选与可见一致
  if (onlyNeed.value) {
    const visibleIds = new Set(filteredEndpoints.value.map((e) => e.id))
    checked.value = checked.value.filter((id) => visibleIds.has(id))
  }
}
const allEpSelected = computed(
  () =>
    filteredEndpoints.value.length > 0 &&
    filteredEndpoints.value.every((e) => checked.value.includes(e.id)),
)
const someEpSelected = computed(() => checked.value.length > 0 && !allEpSelected.value)

function toggleAllEndpoints(val: unknown) {
  const ids = filteredEndpoints.value.map((e) => e.id)
  if (val) checked.value = [...new Set([...checked.value, ...ids])]
  else checked.value = checked.value.filter((id) => !ids.includes(id))
}

async function loadEndpoints() {
  endpointsLoading.value = true
  try {
    const [eps, cases] = await Promise.all([
      apifoxApi.listEndpoints(props.projectId),
      apifoxApi.listProjectCases(props.projectId),
    ])
    endpoints.value = eps
    const counts: Record<number, number> = {}
    for (const c of cases) counts[c.endpoint_id] = (counts[c.endpoint_id] ?? 0) + 1
    caseCounts.value = counts
    if (autoSelectNeed.value) checked.value = eps.filter(needsGen).map((e) => e.id)
  } finally {
    endpointsLoading.value = false
  }
}

function open(preselect?: number[]) {
  resetCategories()
  const hasPreselect = !!preselect && preselect.length > 0
  autoSelectNeed.value = !hasPreselect
  checked.value = hasPreselect ? [...preselect!] : []
  epKeyword.value = ''
  onlyNeed.value = false
  submitting.value = false
  loadProviders()
  loadEndpoints()
  visible.value = true
}
defineExpose({ open })

async function generate() {
  submitting.value = true
  try {
    await store.start(
      Number(props.projectId),
      checked.value.slice(),
      buildCategoriesPayload(),
      providerId.value,
    )
    ElMessage.success('已提交批量生成，请到「AI 任务中心」查看进度与结果')
    emit('created')
    visible.value = false
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || 'AI 任务创建失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.tip {
  color: var(--ax-text-secondary);
  font-size: var(--ax-text-body-sm-size);
  margin-bottom: var(--ax-space-3);
}

.result {
  max-height: 56vh;
  overflow: auto;
}

.ep-block {
  margin-top: var(--ax-space-2);
}

.ep-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
  margin-bottom: var(--ax-space-1-5);
}

.ep-head-right {
  display: flex;
  align-items: center;
  gap: var(--ax-space-3);
}

.ep-flag {
  margin-left: var(--ax-space-2);
}

.ep-list {
  max-height: 240px;
  overflow: auto;
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  padding: var(--ax-space-1-5) var(--ax-space-2);
  margin-top: var(--ax-space-1-5);
}

.ep-row {
  padding: var(--ax-space-0-5) 0;
}

.ep-name {
  margin: 0 var(--ax-space-2);
}

.ep-path {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-caption-size);
}
</style>

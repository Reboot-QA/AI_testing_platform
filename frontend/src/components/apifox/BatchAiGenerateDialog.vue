<template>
  <el-dialog
    v-model="visible"
    title="批量 AI 生成接口测试用例"
    width="720px"
    :close-on-click-modal="false"
  >
    <!-- 配置 -->
    <div v-if="step === 'config'" class="config">
      <div class="tip">
        选择接口并勾选类别，AI 按各接口复杂度批量生成用例。生成在后台进行，可关闭弹窗做其他事。
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
          <el-checkbox
            :model-value="allEpSelected"
            :indeterminate="someEpSelected"
            @change="toggleAllEndpoints"
            >全选</el-checkbox
          >
        </div>
        <el-input v-model="epKeyword" size="small" placeholder="搜索接口名 / 路径" clearable />
        <div v-loading="endpointsLoading" class="ep-list">
          <el-checkbox-group v-model="checked">
            <div v-for="ep in filteredEndpoints" :key="ep.id" class="ep-row">
              <el-checkbox :value="ep.id">
                <MethodTag :method="ep.method" />
                <span class="ep-name">{{ ep.name }}</span>
                <span class="ep-path">{{ ep.path }}</span>
              </el-checkbox>
            </div>
          </el-checkbox-group>
          <el-empty v-if="!filteredEndpoints.length" description="无接口" :image-size="40" />
        </div>
      </div>
    </div>

    <!-- 进度 / 结果 -->
    <div v-else class="result">
      <AiGenTaskProgress v-if="taskId" :task-id="taskId" @applied="onApplied" />
    </div>

    <template #footer>
      <template v-if="step === 'config'">
        <el-button @click="visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="!anyChecked || !checked.length"
          @click="generate"
          >生成（{{ checked.length }} 个接口）</el-button
        >
      </template>
      <template v-else-if="generating">
        <el-button @click="visible = false">关闭（后台继续）</el-button>
        <el-button :loading="canceling" @click="cancel">取消生成</el-button>
      </template>
      <template v-else>
        <el-button @click="backToConfig">再次生成</el-button>
        <el-button type="primary" @click="visible = false">完成</el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useAiGenConfig } from '@/composables/useAiGenConfig'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import AiGenConfigFields from '@/components/apifox/AiGenConfigFields.vue'
import AiGenTaskProgress from '@/components/apifox/AiGenTaskProgress.vue'
import MethodTag from '@/components/apifox/common/MethodTag.vue'

const props = defineProps<{ projectId: string | number }>()
const emit = defineEmits<{ applied: [number] }>()

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
const step = ref<'config' | 'result'>('config')
const submitting = ref(false)
const canceling = ref(false)
const taskId = ref<number | null>(null)
const endpoints = ref<Endpoint[]>([])
const endpointsLoading = ref(false)
const epKeyword = ref('')
const checked = ref<number[]>([])

const task = computed(() => (taskId.value ? store.taskById(taskId.value) : undefined))
const generating = computed(
  () => !!task.value && !['succeeded', 'partial', 'failed', 'canceled'].includes(task.value.status),
)

const filteredEndpoints = computed<Endpoint[]>(() => {
  const kw = epKeyword.value.trim().toLowerCase()
  if (!kw) return endpoints.value
  return endpoints.value.filter(
    (e) => e.name.toLowerCase().includes(kw) || e.path.toLowerCase().includes(kw),
  )
})
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
    endpoints.value = await apifoxApi.listEndpoints(props.projectId)
  } finally {
    endpointsLoading.value = false
  }
}

function open() {
  step.value = 'config'
  resetCategories()
  checked.value = []
  epKeyword.value = ''
  submitting.value = false
  canceling.value = false
  loadProviders()
  loadEndpoints()
  // 会话内若已有进行中的批量任务，重开时回到进度视图
  if (taskId.value && store.taskById(taskId.value)) step.value = 'result'
  visible.value = true
}
defineExpose({ open })

function backToConfig() {
  taskId.value = null
  step.value = 'config'
}

async function generate() {
  submitting.value = true
  try {
    taskId.value = await store.start(
      Number(props.projectId),
      checked.value.slice(),
      buildCategoriesPayload(),
      providerId.value,
    )
    step.value = 'result'
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || 'AI 生成任务创建失败')
  } finally {
    submitting.value = false
  }
}

async function cancel() {
  if (taskId.value === null) return
  canceling.value = true
  try {
    await store.cancel(taskId.value)
    ElMessage.info('已取消生成')
  } catch (e: unknown) {
    ElMessage.error((e as Error).message || '取消失败')
  } finally {
    canceling.value = false
  }
}

function onApplied(endpointId: number) {
  emit('applied', endpointId)
}
</script>

<style scoped>
.tip {
  color: var(--ax-text-secondary);
  font-size: 13px;
  margin-bottom: 12px;
}

.result {
  max-height: 56vh;
  overflow: auto;
}

.ep-block {
  margin-top: 8px;
}

.ep-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  color: var(--ax-text-secondary);
  margin-bottom: 6px;
}

.ep-list {
  max-height: 240px;
  overflow: auto;
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  padding: 6px 10px;
  margin-top: 6px;
}

.ep-row {
  padding: 2px 0;
}

.ep-name {
  margin: 0 8px;
}

.ep-path {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}
</style>

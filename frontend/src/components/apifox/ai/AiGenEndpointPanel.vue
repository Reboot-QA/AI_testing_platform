<template>
  <div class="ai-ep-workspace">
    <header class="ws-head">
      <div class="ws-head-main">
        <h2 class="ws-title">AI 生成单接口用例</h2>
        <div v-if="endpoint" class="ws-ep">
          <MethodTag :method="endpoint.method" />
          <span class="ws-ep-name">{{ endpoint.name }}</span>
          <span class="ws-ep-path">{{ endpoint.path }}</span>
        </div>
      </div>
      <div class="ws-head-actions">
        <el-button v-if="running" size="small" @click="stopTask">
          <el-icon><VideoPause /></el-icon>
          停止
        </el-button>
        <el-button type="primary" size="small" @click="openStart">
          <el-icon><MagicStick /></el-icon>
          {{ taskId ? '重新生成' : '开始生成' }}
        </el-button>
      </div>
    </header>

    <div class="ws-sub">
      <el-radio-group v-model="viewTab" size="small">
        <el-radio-button value="pending">
          待入库{{ pendingCount ? ` (${pendingCount})` : '' }}
        </el-radio-button>
        <el-radio-button value="done">
          已入库{{ appliedCount ? ` (${appliedCount})` : '' }}
        </el-radio-button>
        <el-radio-button value="discarded">
          废弃{{ discardedCount ? ` (${discardedCount})` : '' }}
        </el-radio-button>
      </el-radio-group>
      <el-button link type="primary" class="ws-link-cases" @click="emit('view-cases')">
        查看该接口已有单接口用例 ({{ caseCount }})
        <el-icon><ArrowRight /></el-icon>
      </el-button>
    </div>

    <div class="ws-body">
      <template v-if="taskId && showFullDetail">
        <div v-if="canCollapseDetail" class="detail-toolbar">
          <span class="detail-toolbar-hint">生成详情</span>
          <el-button link type="primary" size="small" @click="collapse">收起详情</el-button>
        </div>
        <AiGenTaskProgress
          :task-id="taskId"
          :project-id="projectId"
          :endpoint-id="Number(endpointId)"
          :endpoint-path="endpoint?.path ?? ''"
          :view="viewTab"
          @applied="onApplied"
        />
      </template>
      <div v-else-if="taskId && showSummary" class="summary-card">
        <div class="summary-main">
          <el-tag size="small" :type="summaryStatusType">{{ summaryStatusText }}</el-tag>
          <span class="summary-line">{{ summaryText }}</span>
        </div>
        <p class="summary-hint">完整生成过程与历史请到 AI 任务中心查看。</p>
        <div class="summary-actions">
          <el-button size="small" @click="expand">展开详情</el-button>
          <el-button size="small" type="primary" plain @click="goAiJobs">
            去 AI 任务中心
          </el-button>
        </div>
      </div>
      <el-empty
        v-else-if="!taskId"
        description="尚未生成本接口用例，点击右上角「开始生成」"
        :image-size="72"
      />
      <el-empty
        v-else
        :description="
          viewTab === 'pending'
            ? '暂无待入库用例'
            : viewTab === 'discarded'
              ? '暂无废弃记录（本任务）'
              : '暂无已入库记录（本任务）'
        "
        :image-size="60"
      />
    </div>

    <AiGenerateCasesDialog
      ref="dialogRef"
      :endpoint-id="endpointId"
      :project-id="projectId"
      @created="onTaskCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, MagicStick, VideoPause } from '@element-plus/icons-vue'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import { useAiGenDetailCollapsed } from '@/composables/useAiGenDetailCollapsed'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import AiGenTaskProgress from '@/components/apifox/ai/AiGenTaskProgress.vue'
import AiGenerateCasesDialog from '@/components/apifox/ai/AiGenerateCasesDialog.vue'

const props = defineProps<{ endpointId: Id; projectId: Id }>()
const emit = defineEmits<{ 'view-cases': []; applied: [] }>()

const route = useRoute()
const router = useRouter()
const store = useApifoxAiGenerateStore()
const endpoint = ref<Schemas['EndpointOut'] | null>(null)
const caseCount = ref(0)
const viewTab = ref<'pending' | 'done' | 'discarded'>('pending')
const dialogRef = ref<InstanceType<typeof AiGenerateCasesDialog> | null>(null)
const endpointIdNum = computed(() => Number(props.endpointId))
const { preferCollapsed, sessionExpanded, collapse, expand } =
  useAiGenDetailCollapsed(endpointIdNum)

const taskId = computed(() => store.latestTaskForEndpoint(Number(props.endpointId))?.id ?? null)
const task = computed(() => (taskId.value ? store.taskById(taskId.value) : undefined))

const running = computed(
  () => !!task.value && !['succeeded', 'partial', 'failed', 'canceled'].includes(task.value.status),
)

const item = computed(() =>
  task.value?.items.find((i) => i.endpoint_id === Number(props.endpointId)),
)

const pendingCount = computed(() => {
  const it = item.value
  if (!it || it.status !== 'succeeded') return 0
  return it.cases.length
})

const appliedCount = computed(() => item.value?.applied_count ?? 0)

const discardedCount = computed(() => item.value?.discarded_cases?.length ?? 0)

const showProgress = computed(() => {
  if (!item.value) return viewTab.value === 'pending' && running.value
  if (viewTab.value === 'pending') {
    return item.value.status === 'succeeded' ? pendingCount.value > 0 || running.value : true
  }
  if (viewTab.value === 'discarded') return discardedCount.value > 0
  return appliedCount.value > 0
})

/** 生成中始终展示；否则尊重「手动收起」记忆，本会话可临时展开 */
const showFullDetail = computed(() => {
  if (!taskId.value || !showProgress.value) return false
  if (running.value) return true
  if (sessionExpanded.value) return true
  return !preferCollapsed.value
})

const showSummary = computed(
  () => !!taskId.value && preferCollapsed.value && !sessionExpanded.value && !running.value,
)

const canCollapseDetail = computed(() => showFullDetail.value && !running.value)

const STATUS_LABELS: Record<string, string> = {
  pending: '排队中',
  running: '生成中',
  succeeded: '生成成功',
  partial: '部分完成',
  failed: '生成失败',
  canceled: '已取消',
}

const summaryStatusText = computed(() => {
  const s = task.value?.status
  return (s && STATUS_LABELS[s]) || s || '—'
})

const summaryStatusType = computed(() => {
  const s = task.value?.status
  if (s === 'succeeded') return 'success'
  if (s === 'failed') return 'danger'
  if (s === 'partial') return 'warning'
  return 'info'
})

const summaryText = computed(() => {
  const parts: string[] = []
  if (pendingCount.value) parts.push(`待入库 ${pendingCount.value} 条`)
  if (appliedCount.value) parts.push(`已入库 ${appliedCount.value} 条`)
  if (discardedCount.value) parts.push(`已废弃 ${discardedCount.value} 条`)
  if (!parts.length) {
    const it = item.value
    if (it?.status === 'failed') return it.error || '生成失败'
    if (it?.status === 'succeeded') return '本任务暂无待入库用例'
    return '可到 AI 任务中心查看完整记录'
  }
  return parts.join(' · ')
})

async function loadMeta() {
  const eid = Number(props.endpointId)
  endpoint.value = await apifoxApi.getEndpoint(eid)
  const list = await apifoxApi.listCases(eid)
  caseCount.value = list.length
}

function openStart() {
  if (running.value) {
    ElMessage.warning('当前任务生成中，请先停止或等待完成')
    return
  }
  dialogRef.value?.open()
}

defineExpose({ openStart, refreshCaseCount: loadMeta })

async function onTaskCreated(id: number) {
  await store.loadTask(id)
  viewTab.value = 'pending'
  // 新任务创建后本会话展开进度，不清除「下次默认收起」记忆
  expand()
}

async function stopTask() {
  if (!taskId.value) return
  await ElMessageBox.confirm('确认停止当前 AI 生成任务？', '停止生成', { type: 'warning' })
  await store.cancel(taskId.value)
  ElMessage.info('已停止生成')
}

function onApplied() {
  loadMeta()
  emit('applied')
}

function goAiJobs() {
  void router.push({ name: 'WorkspaceAiApis', params: route.params })
}

watch(
  () => props.endpointId,
  () => {
    loadMeta()
    viewTab.value = 'pending'
  },
  { immediate: true },
)

onMounted(() => {
  store.resumeActive(Number(props.projectId)).then(() => {
    if (taskId.value) store.loadTask(taskId.value)
  })
})
</script>

<style scoped>
.ai-ep-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--ax-bg);
}

.ws-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--ax-space-2);
  padding: var(--ax-space-2) var(--ax-space-1);
  border-bottom: 1px solid var(--ax-border);
  flex-shrink: 0;
}

.ws-title {
  margin: 0 0 var(--ax-space-1);
  font-size: var(--ax-font-sm);
  font-weight: 600;
  color: var(--ax-text);
}

.ws-ep {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--ax-space-2);
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.ws-ep-name {
  font-weight: 500;
  color: var(--ax-text);
}

.ws-ep-path {
  font-family: Consolas, Monaco, monospace;
  color: var(--ax-text-placeholder);
}

.ws-head-actions {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  flex-shrink: 0;
}

.ws-sub {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-2);
  padding: var(--ax-space-1) var(--ax-space-1);
  border-bottom: 1px solid var(--ax-border);
  flex-shrink: 0;
}

.ws-link-cases {
  font-size: var(--ax-font-sm);
}

.ws-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: var(--ax-space-1) var(--ax-space-1);
}

.detail-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ax-space-2);
}

.detail-toolbar-hint {
  font-size: var(--ax-font-sm);
  font-weight: 600;
  color: var(--ax-text-secondary);
}

.summary-card {
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  background: var(--ax-bg-subtle);
  padding: var(--ax-space-3);
}

.summary-main {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--ax-space-2);
}

.summary-line {
  font-size: var(--ax-font-sm);
  color: var(--ax-text);
}

.summary-hint {
  margin: var(--ax-space-2) 0 0;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-tertiary);
}

.summary-actions {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-top: var(--ax-space-3);
}
</style>

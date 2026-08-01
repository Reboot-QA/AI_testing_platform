<template>
  <div class="func-ov">
    <DomainOverview
      :stats="stats"
      :actions="ACTIONS"
      :steps="STEPS"
      @nav="onNav"
    />
    <OverviewRecentAiSection
      title="最近 AI 生成"
      :loading="recentLoading"
      :rows="recentRows"
      :total="recentTotal"
      :page="recentPage"
      :page-size="PAGE_SIZE"
      show-sub-column
      empty-text="暂无 AI 生成用例，可前往「AI 生成用例」"
      @refresh="loadRecent"
      @page-change="onRecentPage"
      @row-click="(row) => onNav('func-cases', 'kw:' + row.title)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { projectApi, testcaseApi } from '@/api'
import type { Schemas } from '@/api/types'
import DomainOverview from './DomainOverview.vue'
import OverviewRecentAiSection, { type OverviewAiRow } from './OverviewRecentAiSection.vue'
import type { OverviewAction, OverviewStat, OverviewStep } from '@/types/shell'
import { formatBeijingTime } from '@/utils/datetime'
import { useWorkspaceOverviewNav } from '@/composables/useWorkspaceOverviewNav'

const props = defineProps<{ projectId: number }>()
const { navigate: onNav } = useWorkspaceOverviewNav(() => props.projectId, 'functional')

const PAGE_SIZE = 10
const overview = ref<Awaited<ReturnType<typeof projectApi.functionalOverview>> | null>(null)
const recentLoading = ref(false)
const recentPage = ref(1)
const recentTotal = ref(0)
const recentItems = ref<Schemas['TestCaseOut'][]>([])

const STEPS: OverviewStep[] = [
  { label: '维护功能用例', section: 'func-cases' },
  { label: '完成用例评审', section: 'func-cases' },
  { label: '创建测试单', section: 'func-runs' },
  { label: '执行并跟踪结果', section: 'func-runs' },
  { label: '查看测试报告', section: 'func-reports' },
]

const ACTIONS: OverviewAction[] = [
  { label: 'AI 生成用例', section: 'ai', icon: 'MagicStick', primary: true },
  { label: '功能用例库', section: 'func-cases', icon: 'Files' },
  { label: '手工执行', section: 'func-runs', icon: 'VideoPlay' },
  { label: '功能测试报告', section: 'func-reports', icon: 'Document' },
]

const REVIEW_MAP: Record<string, string> = {
  draft: '草稿',
  pending: '待评审',
  approved: '已通过',
  rejected: '已驳回',
}
const REVIEW_TYPE: Record<string, OverviewAiRow['statusType']> = {
  draft: 'info',
  pending: 'warning',
  approved: 'success',
  rejected: 'danger',
}

const stats = computed<OverviewStat[]>(() => {
  const o = overview.value
  if (!o) return []
  return [
    {
      label: '功能用例数',
      value: o.case_total,
      icon: 'Files',
      tone: 'brand',
      section: 'func-cases',
    },
    {
      label: '待评审',
      value: o.pending_review_count,
      icon: 'Clock',
      tone: 'warning',
      section: 'func-cases',
      filter: 'review_pending',
    },
    {
      label: 'AI 生成用例',
      value: o.ai_generated_count,
      icon: 'MagicStick',
      tone: 'brand',
      section: 'func-cases',
      filter: 'ai_generated',
    },
    {
      label: 'AI 待确认',
      value: o.ai_pending_review_count,
      icon: 'Warning',
      tone: 'warning',
      section: 'func-cases',
      filter: 'ai_pending',
    },
    {
      label: '执行中测试单',
      value: o.running_run_count,
      icon: 'VideoPlay',
      tone: 'success',
      section: 'func-runs',
    },
  ]
})

const recentRows = computed<OverviewAiRow[]>(() =>
  recentItems.value.map((item) => ({
    id: item.id,
    title: item.title,
    statusLabel: REVIEW_MAP[item.review_status] || item.review_status,
    statusType: REVIEW_TYPE[item.review_status] || 'info',
    sub: item.requirement_title || undefined,
    createdAt: formatBeijingTime(item.created_at),
  })),
)

async function loadOverview() {
  if (!props.projectId) return
  try {
    overview.value = await projectApi.functionalOverview(props.projectId)
  } catch {
    // 全局拦截器已提示
  }
}

async function loadRecent() {
  if (!props.projectId) return
  recentLoading.value = true
  try {
    const data = await testcaseApi.listPage({
      project_id: props.projectId,
      source: 'ai_generated',
      order: 'created_at_desc',
      page: recentPage.value,
      page_size: PAGE_SIZE,
    })
    recentItems.value = data.items || []
    recentTotal.value = data.total || 0
  } catch {
    // 全局拦截器已提示
  } finally {
    recentLoading.value = false
  }
}

function onRecentPage(page: number) {
  recentPage.value = page
  loadRecent()
}

async function loadAll() {
  recentPage.value = 1
  await Promise.all([loadOverview(), loadRecent()])
}

watch(() => props.projectId, loadAll, { immediate: true })
</script>

<style scoped>
.func-ov {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  padding: var(--ax-space-4);
  box-sizing: border-box;
}

.func-ov :deep(.domain-ov) {
  flex: none;
  padding: 0;
}
</style>

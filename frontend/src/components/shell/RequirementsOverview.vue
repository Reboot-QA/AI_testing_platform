<template>
  <div class="req-ov">
    <DomainOverview
      :stats="stats"
      :actions="ACTIONS"
      :steps="STEPS"
      @nav="onNav"
    />
    <OverviewRecentAiSection
      title="最近 AI 分析"
      :loading="recentLoading"
      :rows="recentRows"
      :total="recentTotal"
      :page="recentPage"
      :page-size="PAGE_SIZE"
      empty-text="暂无 AI 导入需求，可前往「AI 分析需求」"
      @refresh="loadRecent"
      @page-change="onRecentPage"
      @row-click="(row) => onNav('req-points', 'kw:' + row.title)"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { projectApi, requirementApi } from '@/api'
import type { Schemas } from '@/api/types'
import DomainOverview from './DomainOverview.vue'
import OverviewRecentAiSection, { type OverviewAiRow } from './OverviewRecentAiSection.vue'
import type { OverviewAction, OverviewStat, OverviewStep } from '@/types/shell'
import { formatBeijingTime } from '@/utils/datetime'
import { useWorkspaceOverviewNav } from '@/composables/useWorkspaceOverviewNav'

const props = defineProps<{ projectId: number }>()
const { navigate: onNav } = useWorkspaceOverviewNav(() => props.projectId, 'requirements')

const PAGE_SIZE = 10
const overview = ref<Awaited<ReturnType<typeof projectApi.requirementsOverview>> | null>(null)
const recentLoading = ref(false)
const recentPage = ref(1)
const recentTotal = ref(0)
const recentItems = ref<Schemas['RequirementOut'][]>([])

const STEPS: OverviewStep[] = [
  { label: '导入需求文档', section: 'req-docs' },
  { label: 'AI 提取需求点', section: 'req-docs' },
  { label: '人工评审确认', section: 'req-points' },
  { label: '关联功能用例', section: 'req-points' },
]

const ACTIONS: OverviewAction[] = [
  { label: '需求点', section: 'req-points', icon: 'Document', primary: true },
  { label: 'AI 分析需求', section: 'req-docs', icon: 'MagicStick' },
]

const STATUS_MAP: Record<string, string> = {
  draft: '草稿',
  approved: '已评审',
  closed: '已关闭',
}
const STATUS_TYPE: Record<string, OverviewAiRow['statusType']> = {
  draft: 'info',
  approved: 'success',
  closed: 'warning',
}

const stats = computed<OverviewStat[]>(() => {
  const o = overview.value
  if (!o) return []
  return [
    {
      label: '需求点总数',
      value: o.req_total,
      icon: 'Document',
      tone: 'brand',
      section: 'req-points',
    },
    {
      label: '未评审',
      value: o.unreviewed_count,
      icon: 'Clock',
      tone: 'warning',
      section: 'req-points',
      filter: 'unreviewed',
    },
    {
      label: '已关联用例',
      value: o.linked_count,
      icon: 'CircleCheck',
      tone: 'success',
      section: 'req-points',
    },
    {
      label: '未覆盖',
      value: o.unlinked_count,
      icon: 'Warning',
      tone: 'warning',
      section: 'req-points',
      filter: 'unlinked',
    },
    {
      label: 'AI 导入需求',
      value: o.ai_document_count,
      icon: 'MagicStick',
      tone: 'brand',
      section: 'req-points',
      filter: 'ai_document',
    },
  ]
})

const recentRows = computed<OverviewAiRow[]>(() =>
  recentItems.value.map((item) => ({
    id: item.id,
    title: item.title,
    statusLabel: STATUS_MAP[item.status] || item.status,
    statusType: STATUS_TYPE[item.status] || 'info',
    createdAt: formatBeijingTime(item.created_at),
  })),
)

async function loadOverview() {
  if (!props.projectId) return
  try {
    overview.value = await projectApi.requirementsOverview(props.projectId)
  } catch {
    // 全局拦截器已提示
  }
}

async function loadRecent() {
  if (!props.projectId) return
  recentLoading.value = true
  try {
    const data = await requirementApi.listPage(props.projectId, {
      source: 'ai_document',
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
.req-ov {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  padding: var(--ax-space-4);
  box-sizing: border-box;
}

.req-ov :deep(.domain-ov) {
  flex: none;
  padding: 0;
}
</style>

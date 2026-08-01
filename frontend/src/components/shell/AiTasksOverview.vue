<template>
  <div v-loading="overviewLoading" class="ai-tasks-ov">
    <DomainOverview :stats="stats" :actions="ACTIONS" :steps="STEPS" @nav="onNav" />

    <div class="records-grid ov-section mt-4">
      <HubTaskRecentSection
        title="最近 AI 需求任务"
        icon="Document"
        nav-section="ai-req"
        task-type="requirement"
        generated-label="提取需求点"
        :loading="reqLoading"
        :tasks="reqTasks"
        @refresh="loadReqRecent"
        @nav="onNav"
        @task-click="(row) => onTaskNav('ai-req', row)"
      />
      <HubTaskRecentSection
        title="最近 AI 用例任务"
        icon="List"
        nav-section="ai-case"
        task-type="functional"
        generated-label="生成用例"
        :loading="caseLoading"
        :tasks="caseTasks"
        @refresh="loadCaseRecent"
        @nav="onNav"
        @task-click="(row) => onTaskNav('ai-case', row)"
      />
      <section v-loading="apiLoading" class="records">
        <header class="rec-head">
          <span class="rec-title">
            <el-icon><Connection /></el-icon> 最近接口 AI 任务
          </span>
          <div class="rec-head-actions">
            <el-button link size="small" @click="onNav('ai-api')">查看全部</el-button>
            <el-button link size="small" @click="loadApiRecent">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </header>
        <div class="rec-body">
          <ul v-if="apiTasks.length" class="rec-list">
            <li
              v-for="row in apiTasks"
              :key="row.id"
              class="rec-item"
              @click="onTaskNav('ai-api', row)"
            >
              <div class="rec-item-main">
                <el-tag size="small" :type="hubStatusType(row.status)">{{
                  hubStatusText(row.status)
                }}</el-tag>
                <span
                  class="rec-item-target"
                  :title="row.target || `批量 · ${row.total_items} 接口`"
                >
                  {{ row.target || `批量 · ${row.total_items} 接口` }}
                </span>
              </div>
              <div class="rec-item-meta">
                <span
                  >{{ row.done_items }}/{{ row.total_items }} · 生成用例
                  {{ row.generated_total }}</span
                >
                <span>{{ formatTime(row.created_at) }}</span>
              </div>
            </li>
          </ul>
          <el-empty
            v-else-if="!apiLoading"
            class="rec-empty"
            description="暂无接口 AI 任务"
            :image-size="48"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Connection, Refresh } from '@element-plus/icons-vue'
import type { Id } from '@/api/request'
import { apifoxApi, projectApi } from '@/api'
import { hubAiTasksApi, type HubAiTaskBrief } from '@/api/hubAiTasks'
import type { AiTasksOverviewOut } from '@/api/project'
import type { Schemas } from '@/api/types'
import { useWorkspaceOverviewNav } from '@/composables/useWorkspaceOverviewNav'
import DomainOverview from './DomainOverview.vue'
import HubTaskRecentSection from './HubTaskRecentSection.vue'
import type { OverviewAction, OverviewStat, OverviewStep } from '@/types/shell'
import { formatTime } from '@/utils/runFormat'
import { hubStatusText, hubStatusType } from '@/utils/hubAiTaskStatus'

const props = defineProps<{ projectId: Id }>()

const { navigate: onNav } = useWorkspaceOverviewNav(() => props.projectId, 'ai_tasks')

function onTaskNav(section: string, row: { id: number }) {
  onNav(section, undefined, { task: String(row.id) })
}

const RECENT_SIZE = 9

const STEPS: OverviewStep[] = [
  { label: 'AI 解析需求', section: 'ai-req' },
  { label: 'AI 生成用例', section: 'ai-case' },
  { label: 'AI 接口用例', section: 'ai-api' },
  { label: '评审入库', section: 'ai-api' },
]

const ACTIONS: OverviewAction[] = [
  { label: 'AI 需求任务', section: 'ai-req', icon: 'Document', primary: true },
  { label: 'AI 用例任务', section: 'ai-case', icon: 'List' },
  { label: 'AI 接口任务', section: 'ai-api', icon: 'Connection' },
]

const overview = ref<AiTasksOverviewOut | null>(null)
const overviewLoading = ref(false)
const reqLoading = ref(false)
const caseLoading = ref(false)
const apiLoading = ref(false)
const reqTasks = ref<HubAiTaskBrief[]>([])
const caseTasks = ref<HubAiTaskBrief[]>([])
const apiTasks = ref<Schemas['AiGenTaskBrief'][]>([])

const stats = computed<OverviewStat[]>(() => {
  const o = overview.value
  if (!o) return []
  return [
    {
      label: '任务总数',
      value: o.total_task_count,
      icon: 'MagicStick',
      tone: 'brand',
    },
    {
      label: '需求点任务',
      value: o.requirement_task_count,
      icon: 'Document',
      tone: 'brand',
      section: 'ai-req',
    },
    {
      label: '用例任务',
      value: o.case_task_count,
      icon: 'List',
      tone: 'brand',
      section: 'ai-case',
    },
    {
      label: '接口任务',
      value: o.api_task_count,
      icon: 'Connection',
      tone: o.active_api_task_count ? 'warning' : 'brand',
      section: 'ai-api',
    },
  ]
})

async function loadOverview() {
  if (!props.projectId) return
  overviewLoading.value = true
  try {
    overview.value = await projectApi.aiTasksOverview(props.projectId)
  } finally {
    overviewLoading.value = false
  }
}

async function loadReqRecent() {
  if (!props.projectId) return
  reqLoading.value = true
  try {
    const res = await hubAiTasksApi.listTasks(props.projectId, {
      task_type: 'requirement',
      page: 1,
      page_size: RECENT_SIZE,
    })
    reqTasks.value = res.items.slice(0, RECENT_SIZE)
  } finally {
    reqLoading.value = false
  }
}

async function loadCaseRecent() {
  if (!props.projectId) return
  caseLoading.value = true
  try {
    const res = await hubAiTasksApi.listTasks(props.projectId, {
      task_type: 'functional',
      page: 1,
      page_size: RECENT_SIZE,
    })
    caseTasks.value = res.items.slice(0, RECENT_SIZE)
  } finally {
    caseLoading.value = false
  }
}

async function loadApiRecent() {
  if (!props.projectId) return
  apiLoading.value = true
  try {
    const res = await apifoxApi.listAiGenTasks(props.projectId, {
      page: 1,
      page_size: RECENT_SIZE,
    })
    apiTasks.value = res.items.slice(0, RECENT_SIZE)
  } finally {
    apiLoading.value = false
  }
}

async function load() {
  await Promise.all([loadOverview(), loadReqRecent(), loadCaseRecent(), loadApiRecent()])
}

watch(() => props.projectId, load, { immediate: true })
</script>

<style scoped>
.ai-tasks-ov {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  padding: var(--ax-space-5) var(--ax-space-4) var(--ax-space-4);
  box-sizing: border-box;
}

.ai-tasks-ov :deep(.domain-ov) {
  flex: none;
  padding: 0;
}

.records-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--ax-space-3);
  align-items: stretch;
  overflow: hidden;
}

.records {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  height: 100%;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  padding: var(--ax-space-3) var(--ax-space-3-5);
}

.rec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
  flex: none;
}

.rec-head-actions {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1);
  flex: none;
}

.rec-title {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  min-width: 0;
  font-weight: 600;
  font-size: var(--ax-text-body-size);
  color: var(--ax-text);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.rec-body {
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow-y: auto;
}

.rec-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rec-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--ax-space-2) var(--ax-space-2);
  border-radius: var(--ax-radius);
  cursor: pointer;
  transition: background var(--ax-transition);
}

.rec-item:hover {
  background: var(--ax-bg-subtle);
}

.rec-item-main {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  min-width: 0;
}

.rec-item-target {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: var(--ax-font-sm);
  color: var(--ax-text);
}

.rec-item-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-2);
  padding-left: calc(var(--ax-space-2) + 2px);
  font-size: var(--ax-font-xs);
  color: var(--ax-text-tertiary);
}

.rec-item-meta > span:first-child {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.rec-item-meta > span:last-child {
  flex: none;
  white-space: nowrap;
}

.rec-empty {
  padding: var(--ax-space-3) 0;
}

@media (max-width: 1200px) {
  .ai-tasks-ov {
    overflow-y: auto;
  }

  .records-grid {
    flex: none;
    grid-template-columns: 1fr;
    overflow: visible;
  }
}
</style>

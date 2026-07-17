<template>
  <div class="jobs-panel">
    <div class="head">
      <span class="title">AI 生成任务</span>
      <el-button size="small" :loading="loading" @click="reload">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <el-table
      v-loading="loading"
      :data="tasks"
      class="jobs-table"
      size="small"
      @row-click="openDetail"
    >
      <el-table-column label="状态" width="96">
        <template #default="{ row }">
          <el-tag size="small" :type="statusType(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="目标" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.target || `批量 · ${row.total_items} 接口` }}
        </template>
      </el-table-column>
      <el-table-column label="类别" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">{{ categorySummary(row.categories) }}</template>
      </el-table-column>
      <el-table-column label="进度" width="90">
        <template #default="{ row }">{{ row.done_items }}/{{ row.total_items }}</template>
      </el-table-column>
      <el-table-column label="生成用例" width="96">
        <template #default="{ row }">{{ row.generated_total }} 条</template>
      </el-table-column>
      <el-table-column label="创建时间" width="140">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="完成时间" width="140">
        <template #default="{ row }">{{
          row.finished_at ? formatTime(row.finished_at) : '--'
        }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && !tasks.length" description="暂无 AI 生成任务" :image-size="60" />

    <el-pagination
      v-if="total > pageSize"
      small
      layout="prev, pager, next, total"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      class="pager"
      @current-change="onPage"
    />

    <el-drawer v-model="detailVisible" title="AI 生成任务详情" size="660px">
      <AiGenTaskProgress v-if="detailTaskId" :task-id="detailTaskId" @applied="reload" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { useApifoxAiGenerateStore } from '@/stores/apifoxAiGenerate'
import { categoryLabel } from '@/utils/caseCategory'
import AiGenTaskProgress from '@/components/apifox/AiGenTaskProgress.vue'

type TaskRow = Schemas['AiGenTaskBrief']
const TERMINAL = ['succeeded', 'partial', 'failed', 'canceled']
const POLL_MS = 3000

const pid = useRouteParamId()
const store = useApifoxAiGenerateStore()

const tasks = ref<TaskRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const detailVisible = ref(false)
const detailTaskId = ref<number | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function reload() {
  loading.value = true
  try {
    const res = await apifoxApi.listAiGenTasks(pid.value, { page: page.value, page_size: pageSize })
    tasks.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function onPage(p: number) {
  page.value = p
  reload()
}

async function openDetail(row: TaskRow) {
  detailTaskId.value = row.id
  detailVisible.value = true
  try {
    await store.loadTask(row.id) // AiGenTaskProgress 从 store 读该任务
  } catch {
    /* 忽略，抽屉里会显示空 */
  }
}

const statusText = (s: string): string =>
  ({
    pending: '排队中',
    running: '生成中',
    succeeded: '成功',
    partial: '部分成功',
    failed: '失败',
    canceled: '已取消',
  })[s] || s
const statusType = (s: string): string =>
  ({
    succeeded: 'success',
    partial: 'warning',
    failed: 'danger',
    running: 'primary',
    canceled: 'info',
  })[s] || 'info'
const categorySummary = (cats: string[]): string =>
  cats?.length ? cats.map((c) => categoryLabel(c)).join(' · ') : '-'
const formatTime = (t: string): string => (t ? t.slice(0, 16).replace('T', ' ') : '')

// 有进行中的任务时轮询刷新列表（进度、状态实时更新）
function tick() {
  if (tasks.value.some((t) => !TERMINAL.includes(t.status))) reload()
}

onMounted(() => {
  reload()
  pollTimer = setInterval(tick, POLL_MS)
})
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.jobs-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.title {
  font-size: var(--ax-font);
  font-weight: 600;
  color: var(--ax-brand);
}

.jobs-table {
  flex: 1;
  min-height: 0;
  cursor: pointer;
}

.pager {
  margin-top: 10px;
  justify-content: flex-end;
}
</style>

<template>
  <div class="activity-view max-w-[760px]">
    <div class="toolbar">
      <el-radio-group v-model="scope">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="failed">失败</el-radio-button>
        <el-radio-button value="running">运行中</el-radio-button>
        <el-radio-button value="passed">通过</el-radio-button>
      </el-radio-group>
      <el-select v-model="kind" class="kind" placeholder="全部类型">
        <el-option label="全部类型" value="" />
        <el-option label="场景" value="scenario" />
        <el-option label="单接口" value="case" />
        <el-option label="套件" value="suite" />
      </el-select>
      <div class="spacer" />
      <span class="summary">共 {{ total }} 条运行记录</span>
    </div>

    <div v-loading="loading" class="feed">
      <div v-if="reports.length" class="feed-list">
        <ActivityRow
          v-for="r in reports"
          :key="r.run_id"
          :title="r.target_name"
          :sub="sub(r)"
          :reason="r.error_message"
          :status-text="statusText(r)"
          :status-class="statusClass(r)"
          @click="enter(r.project_id)"
        />
      </div>
      <el-empty v-else-if="!loading" description="暂无匹配的运行记录" :image-size="72" />

      <div v-if="total > pageSize" class="pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          small
          background
          @current-change="load"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { WorkbenchReportItem } from '@/api/apifox'
import { apifoxApi } from '@/api'
import { formatRelativeTime } from '@/utils/datetime'
import ActivityRow from '@/components/hub/ActivityRow.vue'

// 跨项目运行记录 feed。分段(status)/类型(target_type)为服务端筛选 + 分页。
const router = useRouter()
const scope = ref<'all' | 'failed' | 'running' | 'passed'>('all')
const kind = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)
const loading = ref(false)
const reports = ref<WorkbenchReportItem[]>([])

const TYPE_LABEL: Record<string, string> = { scenario: '场景', case: '单接口', suite: '套件' }
const typeLabel = (t: string) => TYPE_LABEL[t] || '用例'
const sub = (r: WorkbenchReportItem) =>
  `${typeLabel(r.target_type)} · ${r.project_name} · ${formatRelativeTime(r.started_at)}`

function statusClass(r: WorkbenchReportItem) {
  if (r.status === 'running') return 'run'
  return r.status === 'passed' ? 'ok' : 'bad'
}
function statusText(r: WorkbenchReportItem) {
  if (r.status === 'running') return '运行中'
  const label = r.status === 'passed' ? '通过' : '失败'
  return r.total_count > 0 ? `${label} ${r.passed_count}/${r.total_count}` : label
}

async function load() {
  loading.value = true
  try {
    const data = await apifoxApi.workbenchReports({
      page: page.value,
      page_size: pageSize,
      status: scope.value === 'all' ? undefined : scope.value,
      target_type: kind.value || undefined,
    })
    reports.value = data.items
    total.value = data.total
  } catch {
    // 全局拦截器已提示
  } finally {
    loading.value = false
  }
}

// 分段/类型变更 → 回到第一页并服务端重新筛选
watch([scope, kind], () => {
  page.value = 1
  load()
})

function enter(projectId: number) {
  router.push({
    path: `/hub/workspace/${projectId}`,
    hash: '#domain=automation&biz=reports&section=reports',
  })
}

onMounted(load)
</script>

<style scoped>
.activity-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
  min-height: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: var(--ax-toolbar-gap);
  flex: none;
}

.kind {
  width: 150px;
}

.spacer {
  flex: 1;
}

.summary {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-tertiary);
}

.feed {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  overflow: hidden;
}

.feed-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.pager {
  flex: none;
  display: flex;
  justify-content: center;
  padding: var(--ax-space-2);
  border-top: 1px solid var(--ax-border);
  background: var(--ax-bg-subtle);
}
</style>

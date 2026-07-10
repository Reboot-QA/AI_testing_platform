<template>
  <div class="card">
    <div class="card-h">最近报告</div>
    <div class="tablewrap">
      <table class="grid">
        <thead>
          <tr><th>报告</th><th>环境</th><th>结果</th><th>时间</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in reports" :key="r.run_id" class="clickable" @click="$emit('open', r)">
            <td>
              <div class="nm">{{ r.target_name }}</div>
              <div class="sb">{{ r.project_name }}</div>
            </td>
            <td>{{ r.environment_name || '-' }}</td>
            <td><span class="pill" :class="pillClass(r)">{{ pillText(r) }}</span></td>
            <td class="mono">{{ time(r.started_at) }}</td>
          </tr>
        </tbody>
      </table>
      <el-empty v-if="!reports.length" description="暂无运行记录" :image-size="48" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  reports: { type: Array, default: () => [] },
})
defineEmits(['open'])

const time = (v) => (v ? new Date(v).toLocaleString('zh-CN', { hour12: false }) : '-')

function pillClass(r) {
  if (r.status === 'running') return 'run'
  return r.status === 'passed' ? 'ok' : 'bad'
}

function pillText(r) {
  if (r.status === 'running') return '运行中'
  const label = r.status === 'passed' ? '通过' : '失败'
  return `${label} ${r.passed_count}/${r.total_count}`
}
</script>

<style scoped>
.card {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}

.card-h {
  padding: 12px 16px;
  border-bottom: 1px solid var(--ax-border);
  font-weight: 600;
}

.tablewrap {
  overflow: auto;
  flex: 1;
}

table.grid {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

table.grid th {
  position: sticky;
  top: 0;
  text-align: left;
  font-weight: 500;
  color: var(--ax-text-secondary);
  padding: 10px 14px;
  background: var(--ax-bg-subtle);
  border-bottom: 1px solid var(--ax-border);
  white-space: nowrap;
}

table.grid td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--ax-border);
  color: var(--ax-text-secondary);
  vertical-align: top;
}

table.grid tr.clickable { cursor: pointer; }
table.grid tr.clickable:hover td { background: var(--ax-bg-subtle); }

.nm { font-weight: 600; color: var(--ax-text); }
.sb { color: var(--ax-text-tertiary); font-size: 12px; }
.mono { font-variant-numeric: tabular-nums; white-space: nowrap; }

.pill {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 20px;
  white-space: nowrap;
}

.pill.ok { color: var(--color-green-6); background: rgba(103, 194, 58, 0.12); }
.pill.bad { color: var(--color-red-6, #f56c6c); background: rgba(245, 108, 108, 0.12); }
.pill.run { color: var(--color-blue-6); background: rgba(64, 128, 255, 0.1); }
</style>

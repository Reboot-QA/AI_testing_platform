<template>
  <section v-loading="loading" class="records">
    <header class="rec-head">
      <div class="rec-head-main">
        <span class="rec-title">
          <el-icon class="rec-title-ic"><MagicStick /></el-icon>
          {{ title }}
        </span>
        <span v-if="total" class="rec-count">{{ total }} 条</span>
      </div>
      <el-button link size="small" @click="emit('refresh')">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </header>

    <div class="rec-body">
      <el-table
        v-if="rows.length"
        :data="rows"
        class="rec-table"
        stripe
        highlight-current-row
        @row-click="(row: OverviewAiRow) => emit('row-click', row)"
      >
        <el-table-column prop="title" label="标题" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="108">
          <template #default="{ row }">
            <el-tag size="small" :type="row.statusType || ''">{{ row.statusLabel }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column
          v-if="showSubColumn"
          label="关联需求"
          min-width="160"
          show-overflow-tooltip
        >
          <template #default="{ row }">{{ row.sub || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="168">
          <template #default="{ row }">{{ row.createdAt }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-else-if="!loading" class="rec-empty" :description="emptyText" :image-size="72" />
    </div>

    <footer v-if="showPager" class="rec-foot">
      <el-pagination
        :current-page="page"
        class="rec-pager"
        background
        size="small"
        layout="total, prev, pager, next"
        :page-size="pageSize"
        :total="total"
        @current-change="(p: number) => emit('page-change', p)"
      />
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface OverviewAiRow {
  id: number
  title: string
  statusLabel: string
  statusType?: '' | 'success' | 'warning' | 'info' | 'danger'
  sub?: string
  createdAt: string
}

const props = defineProps<{
  title: string
  loading: boolean
  rows: OverviewAiRow[]
  total: number
  page: number
  pageSize: number
  emptyText: string
  showSubColumn?: boolean
}>()

/** 总数超页容量，或当前页未拉全（与后端默认 page_size 不一致时兜底） */
const showPager = computed(
  () => props.total > props.pageSize || props.total > props.rows.length,
)

const emit = defineEmits<{
  refresh: []
  'page-change': [page: number]
  'row-click': [row: OverviewAiRow]
}>()
</script>

<style scoped>
.records {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: var(--ax-space-4);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
  overflow: hidden;
}

.rec-head {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-3);
  padding: var(--ax-space-3) var(--ax-space-4);
  border-bottom: 1px solid var(--ax-border);
  background: color-mix(in srgb, var(--ax-bg-subtle) 65%, var(--ax-bg));
}

.rec-head-main {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  min-width: 0;
}

.rec-title {
  display: inline-flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  font-weight: 600;
  color: var(--ax-text);
  font-size: var(--ax-font-base);
}

.rec-title-ic {
  color: var(--ax-rail-active-bg);
}

.rec-count {
  flex: none;
  padding: 2px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--ax-rail-active-bg) 10%, var(--ax-bg));
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-xs);
  font-variant-numeric: tabular-nums;
}

.rec-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 var(--ax-space-1);
}

.rec-table {
  width: 100%;
  cursor: pointer;
}

.rec-table :deep(.el-table__header th) {
  background: var(--ax-bg-subtle);
  color: var(--ax-text-secondary);
  font-weight: 600;
}

.rec-table :deep(.el-table__row) {
  transition: background var(--ax-transition);
}

.rec-empty {
  height: 100%;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rec-foot {
  flex: none;
  display: flex;
  justify-content: flex-end;
  padding: var(--ax-space-2-5) var(--ax-space-4);
  border-top: 1px solid var(--ax-border);
  background: var(--ax-bg);
}

.rec-pager {
  justify-content: flex-end;
}
</style>

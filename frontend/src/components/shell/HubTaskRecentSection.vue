<template>
  <section v-loading="loading" class="records">
    <header class="rec-head">
      <span class="rec-title">
        <el-icon><component :is="iconComponent" /></el-icon> {{ title }}
      </span>
      <div class="rec-head-actions">
        <el-button link size="small" @click="emit('nav', navSection)">查看全部</el-button>
        <el-button link size="small" @click="emit('refresh')">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </header>
    <div class="rec-body">
      <ul v-if="tasks.length" class="rec-list">
        <li v-for="row in tasks" :key="row.id" class="rec-item" @click="emit('task-click', row)">
          <div class="rec-item-main">
            <el-tag size="small" :type="hubStatusType(row.status)">{{
              hubStatusText(row.status)
            }}</el-tag>
            <span class="rec-item-target" :title="row.target || undefined">{{
              row.target || '—'
            }}</span>
          </div>
          <div class="rec-item-meta">
            <span>{{ progressText(row) }}</span>
            <span>{{ formatTime(row.created_at) }}</span>
          </div>
        </li>
      </ul>
      <el-empty v-else-if="!loading" class="rec-empty" :description="emptyText" :image-size="48" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Document, List, Refresh } from '@element-plus/icons-vue'
import type { HubAiTaskBrief, HubAiTaskType } from '@/api/hubAiTasks'
import { formatTime } from '@/utils/runFormat'
import { hubStatusText, hubStatusType } from '@/utils/hubAiTaskStatus'

const ICONS: Record<string, typeof Document> = {
  Document,
  List,
}

const props = defineProps<{
  title: string
  icon: keyof typeof ICONS | string
  navSection: string
  taskType: HubAiTaskType
  generatedLabel: string
  loading: boolean
  tasks: HubAiTaskBrief[]
}>()

const iconComponent = computed(() => ICONS[props.icon] || Document)

const emit = defineEmits<{
  refresh: []
  nav: [section: string]
  'task-click': [row: HubAiTaskBrief]
}>()

const emptyText = computed(() =>
  props.taskType === 'requirement'
    ? '暂无 AI 需求任务，可前往「AI 需求任务」创建'
    : '暂无 AI 用例任务，可前往「AI 用例任务」创建',
)

function progressText(row: HubAiTaskBrief): string {
  if (props.taskType === 'requirement') {
    return `${props.generatedLabel} ${row.generated_total} 条`
  }
  return `${row.done_items}/${row.total_items} · ${props.generatedLabel} ${row.generated_total}`
}
</script>

<style scoped>
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
</style>

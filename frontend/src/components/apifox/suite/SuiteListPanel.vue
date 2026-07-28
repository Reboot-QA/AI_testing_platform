<template>
  <div class="list-panel">
    <div class="panel-head">
      <span class="panel-title">测试套件</span>
      <el-button type="primary" size="small" title="新建套件" @click="$emit('add')">
        <el-icon><Plus /></el-icon>
      </el-button>
    </div>
    <div
      v-for="s in suites"
      :key="s.id"
      class="suite-row"
      :class="{ 'suite-row--active': activeId === s.id }"
      @click="$emit('select', s.id)"
    >
      <el-icon class="suite-row-icon"><Files /></el-icon>
      <el-tooltip :content="s.name" placement="right" :show-after="600">
        <span class="suite-name">{{ s.name }}</span>
      </el-tooltip>
      <span class="suite-meta">{{ s.item_count }} 项</span>
      <el-icon class="suite-action" title="复制套件" @click.stop="$emit('copy', s)">
        <CopyDocument />
      </el-icon>
      <el-icon class="suite-del" title="删除套件" @click.stop="$emit('del', s)">
        <Delete />
      </el-icon>
    </div>
    <el-empty v-if="suites.length === 0" description="暂无套件" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { CopyDocument, Delete, Files, Plus } from '@element-plus/icons-vue'
import type { Schemas } from '@/api/types'

type SuiteBrief = Schemas['SuiteBrief']

defineProps<{ suites: SuiteBrief[]; activeId: number | null }>()

defineEmits<{
  add: []
  select: [id: number]
  copy: [suite: SuiteBrief]
  del: [suite: SuiteBrief]
}>()
</script>

<style scoped>
/* 字号阶梯：面板标题 14 > 套件名 12 > 元信息 11；list-panel/panel-head 见 apifox-workspace.css */
.suite-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  padding: var(--ax-space-1-5) var(--ax-space-1-5) var(--ax-space-1-5) var(--ax-space-2);
  border-radius: 4px;
  cursor: pointer;
}

.suite-row:hover {
  background: var(--ax-bg-hover);
}

.suite-row--active {
  background: var(--ax-bg-active);
}

.suite-row-icon {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-tertiary);
}

.suite-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-font-sm);
  font-weight: 400;
  line-height: var(--ax-leading-compact);
  color: var(--ax-text);
}

.suite-meta {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  line-height: var(--ax-leading-tight);
  color: var(--ax-text-placeholder);
  font-variant-numeric: tabular-nums;
}

.suite-action {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  cursor: pointer;
  color: var(--ax-text-placeholder);
  transition: color 0.15s;
}

.suite-action:hover {
  color: var(--ax-brand);
}

.suite-del {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  cursor: pointer;
  color: var(--ax-text-placeholder);
  transition: color 0.15s;
}

.suite-del:hover {
  color: var(--el-color-danger);
}

.list-panel :deep(.el-empty__description) {
  font-size: var(--ax-font-xs);
}
</style>

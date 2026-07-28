<template>
  <el-dropdown trigger="click" @command="onCommand">
    <button type="button" class="tabbar-more" title="批量关闭标签">
      <el-icon><MoreFilled /></el-icon>
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="left" :disabled="disabled.left">关闭左边</el-dropdown-item>
        <el-dropdown-item command="right" :disabled="disabled.right">关闭右边</el-dropdown-item>
        <el-dropdown-item command="others" :disabled="disabled.others">关闭其他</el-dropdown-item>
        <el-dropdown-item command="all" :disabled="disabled.all" divided>关闭全部</el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import type { BatchCloseCommand } from '@/composables/useTabbarBatchClose'

defineProps<{
  disabled: Record<BatchCloseCommand, boolean>
}>()

const emit = defineEmits<{
  command: [BatchCloseCommand]
}>()

function onCommand(cmd: BatchCloseCommand) {
  emit('command', cmd)
}
</script>

<style scoped>
.tabbar-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  margin-left: var(--ax-space-1);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg-subtle);
  color: var(--ax-text-secondary);
  cursor: pointer;
}

.tabbar-more:hover {
  color: var(--ax-brand);
  border-color: var(--ax-brand);
}
</style>

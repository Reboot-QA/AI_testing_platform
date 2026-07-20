<template>
  <el-empty :description="`「${sectionTitle}」建设中（P2 实现）`">
    <template #image>
      <el-icon :size="48" color="var(--ax-text-disabled)"><Tools /></el-icon>
    </template>
    <div class="ctx">当前项目：{{ store.currentProjectName || '-' }}</div>
  </el-empty>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useWorkspaceStore } from '@/stores/workspace'

const route = useRoute()
const store = useWorkspaceStore()

const sectionTitle = computed(() => route.meta.sectionTitle || '栏目')
</script>

<style scoped>
.ctx {
  color: var(--ax-text-placeholder);
  font-size: 13px;
  margin-top: 8px;
}
</style>

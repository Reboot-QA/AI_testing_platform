<template>
  <div class="stat-row">
    <div v-for="s in stats" :key="s.label" class="stat-card">
      <el-icon class="stat-icon" :color="s.color"><component :is="s.icon" /></el-icon>
      <div class="stat-body">
        <div class="stat-num">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Folder, Document, Tickets } from '@element-plus/icons-vue'

const props = defineProps({
  projects: { type: Array, default: () => [] },
})

const stats = computed(() => {
  const reqs = props.projects.reduce((sum, p) => sum + (p.requirement_count || 0), 0)
  const cases = props.projects.reduce((sum, p) => sum + (p.testcase_count || 0), 0)
  return [
    { label: '项目', value: props.projects.length, icon: Folder, color: 'var(--color-blue-6)' },
    { label: '需求总数', value: reqs, icon: Document, color: 'var(--color-pink-6)' },
    { label: '用例总数', value: cases, icon: Tickets, color: 'var(--color-green-6)' },
  ]
})
</script>

<style scoped>
.stat-row {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1;
  min-width: 160px;
  padding: 16px 20px;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg-subtle);
}

.stat-icon {
  font-size: 28px;
}

.stat-num {
  font-size: 24px;
  font-weight: 700;
  color: var(--ax-text);
  line-height: 1.1;
}

.stat-label {
  font-size: 13px;
  color: var(--ax-text-secondary);
}
</style>

<template>
  <div class="empty">
    <el-icon class="empty-ico"><component :is="icon" /></el-icon>
    <p class="empty-title">{{ title }}</p>
    <p v-if="hint" class="empty-hint">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{ icon: string; title: string; hint?: string }>()
</script>

<style scoped>
.empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ax-space-1-5);
  padding: var(--ax-space-8) var(--ax-space-5);
  text-align: center;
}

.empty-ico {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 20px;
  color: var(--ax-text-placeholder);
  background: var(--ax-bg-subtle);
}

.empty-title {
  margin: 0;
  font-size: var(--ax-text-body-sm-size);
  font-weight: 600;
  color: var(--ax-text-secondary);
}

.empty-hint {
  margin: 0;
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-placeholder);
  max-width: 220px;
  line-height: var(--ax-leading-relaxed);
}
</style>

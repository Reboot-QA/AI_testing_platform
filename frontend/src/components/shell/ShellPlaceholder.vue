<template>
  <div class="ph">
    <el-icon class="ph-ico"><Tools /></el-icon>
    <p class="ph-title">{{ title }}</p>
    <p v-if="hint" class="ph-hint">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title: string; hint?: string }>()
</script>

<style scoped>
.ph {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ax-space-2);
  text-align: center;
}

.ph-ico {
  font-size: 40px;
  color: var(--ax-text-placeholder);
}

.ph-title {
  margin: 0;
  font-weight: 600;
  color: var(--ax-text-secondary);
}

.ph-hint {
  margin: 0;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
  max-width: 420px;
  line-height: var(--ax-leading-relaxed);
}
</style>

<template>
  <div class="result-list">
    <div
      v-for="(item, i) in items"
      :key="i"
      class="result-item"
      :class="item.passed ? 'result-item--ok' : 'result-item--fail'"
    >
      <span class="result-badge">{{ item.label }}</span>
      <span class="result-msg">{{ item.message }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  items: { passed: boolean; label: string; message: string }[]
}>()
</script>

<style scoped>
.result-list {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-1-5);
}

.result-item {
  display: flex;
  align-items: flex-start;
  gap: var(--ax-space-2);
  padding: var(--ax-space-2) var(--ax-space-3);
  border-radius: var(--ax-radius-sm);
  border: 1px solid var(--ax-border);
  background: var(--ax-bg);
  font-size: var(--ax-font-sm);
  line-height: 1.5;
}

.result-item--ok {
  border-color: color-mix(in srgb, var(--ax-success) 25%, var(--ax-border));
  background: color-mix(in srgb, var(--ax-success) 6%, var(--ax-bg));
}

.result-item--fail {
  border-color: color-mix(in srgb, var(--color-pink-6) 25%, var(--ax-border));
  background: color-mix(in srgb, var(--color-pink-6) 6%, var(--ax-bg));
}

.result-badge {
  flex-shrink: 0;
  min-width: 36px;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
}

.result-item--ok .result-badge {
  color: var(--ax-success);
  background: color-mix(in srgb, var(--ax-success) 14%, var(--ax-bg));
}

.result-item--fail .result-badge {
  color: var(--color-pink-6);
  background: color-mix(in srgb, var(--color-pink-6) 14%, var(--ax-bg));
}

.result-msg {
  color: var(--ax-text);
  word-break: break-word;
}
</style>

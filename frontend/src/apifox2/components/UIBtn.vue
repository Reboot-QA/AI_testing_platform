<template>
  <button type="button" class="a2-uibtn" :class="{ primary }">
    <slot />
  </button>
</template>

<script setup lang="ts">
defineProps<{ primary?: boolean }>()
</script>

<style scoped>
.a2-uibtn {
  padding: 4px 8px;
  border: none;
  outline: none;
  cursor: pointer;
  font-size: 12px;
  border-radius: 4px;
  background-color: var(--a2-color-fill-tertiary);
  color: var(--a2-color-text-secondary);
}

.a2-uibtn:hover {
  background-color: var(--a2-color-fill-secondary);
}

.a2-uibtn.primary {
  background-color: rgba(255, 77, 79, 0.1);
  color: var(--a2-color-primary);
}

.a2-uibtn.primary:hover {
  background-color: rgba(255, 77, 79, 0.15);
}
</style>

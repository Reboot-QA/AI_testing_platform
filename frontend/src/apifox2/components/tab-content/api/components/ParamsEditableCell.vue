<template>
  <div class="a2-cell" :class="{ 'validate-error': validateError }">
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ validateError?: boolean }>()
</script>

<style scoped>
.a2-cell {
  display: flex;
  align-items: center;
  height: 100%;
  min-height: 32px;
  outline: 1px solid transparent;
}

.a2-cell:hover,
.a2-cell:focus-within {
  outline-color: var(--a2-color-primary);
}

.a2-cell.validate-error,
.a2-cell.validate-error:hover,
.a2-cell.validate-error:focus-within {
  outline-color: var(--color-red-6, #f5222d);
}
</style>

<template>
  <span class="a2-menu-action-btn" @click="onClick">
    <slot />
  </span>
</template>

<script setup lang="ts">
const emit = defineEmits<{ click: [MouseEvent] }>()

function onClick(e: MouseEvent) {
  emit('click', e)
}
</script>

<style scoped>
.a2-menu-action-btn {
  display: inline-flex;
  height: 100%;
  align-items: center;
  padding: 2px 4px;
  border-radius: 2px;
  cursor: pointer;
}

.a2-menu-action-btn:hover {
  background-color: var(--a2-color-fill-secondary);
}
</style>

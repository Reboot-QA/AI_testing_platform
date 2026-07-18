<template>
  <div :style="{ display: shouldExpand ? 'block' : 'none' }">
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ shouldExpand?: boolean }>()
</script>

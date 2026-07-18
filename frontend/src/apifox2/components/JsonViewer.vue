<template>
  <VueJsonPretty v-if="parsed !== undefined" :data="parsed" :deep="3" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VueJsonPretty from 'vue-json-pretty'
import 'vue-json-pretty/lib/styles.css'

const props = defineProps<{ value?: string }>()

const parsed = computed(() => {
  if (!props.value) return undefined
  try {
    return JSON.parse(props.value)
  } catch {
    return undefined
  }
})
</script>

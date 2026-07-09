<template>
  <span class="method-tag" :style="{ color }">{{ text }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { methodConfig } from '@/config/apifoxConfig'

const props = defineProps({
  method: { type: String, default: 'GET' },
})

const cfg = computed(() => methodConfig(props.method))
const text = computed(() => cfg.value.text)
const color = computed(() => cfg.value.color)
</script>

<style scoped>
.method-tag {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.3px;
}
</style>

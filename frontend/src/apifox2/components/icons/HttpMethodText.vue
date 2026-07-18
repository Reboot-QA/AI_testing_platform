<template>
  <span v-if="config" :class="className" :style="{ color: `var(${config.color})` }">
    {{ text ?? config.text }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { HTTP_METHOD_CONFIG } from '@/apifox2/configs/static'
import type { HttpMethod } from '@/apifox2/enums'

const props = defineProps<{
  method?: HttpMethod
  className?: string
  text?: string
}>()

const config = computed(() => (props.method ? HTTP_METHOD_CONFIG[props.method] : undefined))
</script>

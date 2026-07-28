<template>
  <span class="llm-provider-label">
    <template v-for="(part, index) in parts" :key="index">
      <span v-if="isParenHighlightPart(part)" class="llm-provider-label__paren">{{ part }}</span>
      <span v-else>{{ part }}</span>
    </template>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { isParenHighlightPart, splitParenHighlightParts } from '@/utils/llmProviderLabel'

const props = defineProps<{ text: string }>()

const parts = computed(() => splitParenHighlightParts(props.text))
</script>

<style scoped>
.llm-provider-label__paren {
  color: var(--ax-brand);
}
</style>

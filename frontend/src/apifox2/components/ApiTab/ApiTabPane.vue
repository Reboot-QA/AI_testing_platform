<template>
  <div class="a2-tab-pane">
    <ApiTabContent />
  </div>
</template>

<script setup lang="ts">
import ApiTabContent from './ApiTabContent.vue'
import type { ApiTabItem } from './ApiTab.type'
import { provideTabContent } from '@/apifox2/composables/useTabContent'

const props = defineProps<{ tab: ApiTabItem }>()

// 每个页签提供自己的 tabData（对应 TabContentProvider）。
provideTabContent(props.tab)
</script>

<style scoped>
.a2-tab-pane {
  height: 100%;
}
</style>

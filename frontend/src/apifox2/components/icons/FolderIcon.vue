<template>
  <LayoutIcon
    v-if="type === CatalogType.Overview"
    :size="finalSize"
    :class="className"
    :style="style"
  />
  <UnplugIcon
    v-else-if="type === CatalogType.Http"
    :size="finalSize"
    :class="className"
    :style="style"
  />
  <TrashIcon
    v-else-if="type === CatalogType.Recycle"
    :size="finalSize"
    :class="className"
    :style="style"
  />
  <FileIcon v-else :type="type" :size="finalSize" :class-name="className" :style="style" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CSSProperties } from 'vue'
import { LayoutIcon, TrashIcon, UnplugIcon } from 'lucide-vue-next'
import { CatalogType } from '@/apifox2/enums'
import type { TabContentType } from '@/apifox2/types'
import FileIcon from './FileIcon.vue'

const props = defineProps<{
  type: TabContentType
  size?: number
  className?: string
  style?: CSSProperties
}>()

const finalSize = computed<number>(() => props.size ?? 16)
</script>

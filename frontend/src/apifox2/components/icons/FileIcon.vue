<template>
  <UnplugIcon v-if="isHttp" :size="size" :class="className" :style="style" />
  <PackageIcon v-else-if="isSchema" :size="size" :class="className" :style="style" />
  <ZapIcon v-else-if="isRequest" :size="size" :class="className" :style="style" />
  <FileMinusIcon v-else-if="isDoc" :size="size" :class="className" :style="style" />
  <FolderClosedIcon v-else-if="isFolder" :size="size" :class="className" :style="style" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CSSProperties } from 'vue'
import { FileMinusIcon, FolderClosedIcon, PackageIcon, UnplugIcon, ZapIcon } from 'lucide-vue-next'
import { CatalogType, MenuItemType } from '@/apifox2/enums'
import type { TabContentType } from '@/apifox2/types'

const props = defineProps<{
  type: TabContentType
  size?: number
  className?: string
  style?: CSSProperties
}>()

const isHttp = computed(
  () => props.type === CatalogType.Http || props.type === MenuItemType.ApiDetail,
)
const isSchema = computed(
  () => props.type === CatalogType.Schema || props.type === MenuItemType.ApiSchema,
)
const isRequest = computed(
  () => props.type === CatalogType.Request || props.type === MenuItemType.HttpRequest,
)
const isDoc = computed(() => props.type === CatalogType.Markdown || props.type === MenuItemType.Doc)
const isFolder = computed(
  () => props.type === MenuItemType.ApiDetailFolder || props.type === MenuItemType.ApiSchemaFolder,
)
</script>

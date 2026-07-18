<template>
  <span class="a2-tab-label-inner">
    <span v-if="menuMethodVisible" class="a2-tab-method">
      <HttpMethodText :method="menuMethod" />
    </span>
    <span
      v-else-if="
        tabItem.contentType === MenuItemType.ApiDetail &&
        tabItem.data?.tabStatus === PageTabStatus.Create
      "
      class="a2-tab-method"
    >
      <HttpMethodText :method="initialCreateApiDetailsData.method" />
    </span>
    <FolderIcon v-else :type="tabItem.contentType" :size="16" :style="{ color: labelColor }" />
    <span>{{ menuData?.name ?? tabItem.label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import FolderIcon from '@/apifox2/components/icons/FolderIcon.vue'
import HttpMethodText from '@/apifox2/components/icons/HttpMethodText.vue'
import { PageTabStatus } from '@/apifox2/components/ApiTab/ApiTab.enum'
import type { ApiTabItem } from '@/apifox2/components/ApiTab/ApiTab.type'
import type { ApiMenuData } from '@/apifox2/components/ApiMenu'
import { API_MENU_CONFIG } from '@/apifox2/configs/static'
import { initialCreateApiDetailsData } from '@/apifox2/data/remote'
import { MenuItemType } from '@/apifox2/enums'
import type { HttpMethod } from '@/apifox2/enums'
import type { ApiDetails } from '@/apifox2/types'
import { getCatalogType, getCreateType, hasAccentColor, isCreateType } from '@/apifox2/helpers'

const props = defineProps<{
  menuData?: ApiMenuData
  tabItem: ApiTabItem
}>()

const menuMethodVisible = computed(
  () =>
    props.menuData?.type === MenuItemType.ApiDetail ||
    props.menuData?.type === MenuItemType.HttpRequest,
)

const menuMethod = computed<HttpMethod | undefined>(() => {
  const md = props.menuData
  if (md?.type === MenuItemType.ApiDetail || md?.type === MenuItemType.HttpRequest) {
    return (md.data as ApiDetails | undefined)?.method
  }
  return undefined
})

const labelColor = computed(() => {
  const ct = props.tabItem.contentType
  return isCreateType(ct) && hasAccentColor(ct)
    ? API_MENU_CONFIG[getCatalogType(getCreateType(ct))].accentColor
    : undefined
})
</script>

<style scoped>
.a2-tab-label-inner {
  display: flex;
  align-items: center;
  gap: 4px;
}

.a2-tab-method {
  margin-right: 4px;
  font-weight: 600;
}
</style>

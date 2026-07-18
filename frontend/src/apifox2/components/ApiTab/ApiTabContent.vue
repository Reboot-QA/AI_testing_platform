<template>
  <Api v-if="ct === MenuItemType.ApiDetail" />
  <div v-else-if="ct === MenuItemType.HttpRequest" class="a2-tab-wrapper">
    <ApiDocEditing />
  </div>
  <Schema v-else-if="ct === MenuItemType.ApiSchema" />
  <Folder v-else-if="ct === MenuItemType.ApiDetailFolder || ct === MenuItemType.ApiSchemaFolder" />
  <Doc v-else-if="ct === MenuItemType.Doc" />
  <Overview v-else-if="ct === CatalogType.Overview" />
  <Recycle v-else-if="ct === CatalogType.Recycle" />
  <Blank v-else-if="ct === 'blank'" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Api from '@/apifox2/components/tab-content/api/Api.vue'
import ApiDocEditing from '@/apifox2/components/tab-content/api/ApiDocEditing.vue'
import Schema from '@/apifox2/components/tab-content/Schema.vue'
import Folder from '@/apifox2/components/tab-content/folder/Folder.vue'
import Doc from '@/apifox2/components/tab-content/Doc.vue'
import Overview from '@/apifox2/components/tab-content/Overview.vue'
import Recycle from '@/apifox2/components/tab-content/Recycle.vue'
import Blank from '@/apifox2/components/tab-content/Blank.vue'
import { CatalogType, MenuItemType } from '@/apifox2/enums'
import { useTabContentContext } from '@/apifox2/composables/useTabContent'

const { tabData } = useTabContentContext()
const ct = computed(() => tabData.contentType)
</script>

<style scoped>
.a2-tab-wrapper {
  height: 100%;
}
</style>

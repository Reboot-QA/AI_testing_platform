<template>
  <el-table :data="dataSource" row-key="id">
    <el-table-column type="selection" width="40" />
    <el-table-column label="接口名称" prop="name" />
    <el-table-column label="请求类型">
      <template #default="{ row }">
        <HttpMethodText class="a2-fal-method" :method="row.method" />
      </template>
    </el-table-column>
    <el-table-column label="接口路径" prop="path" />
    <el-table-column label="接口分组" prop="groupPath" />
  </el-table>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import HttpMethodText from '@/apifox2/components/icons/HttpMethodText.vue'
import { MenuItemType } from '@/apifox2/enums'
import { findChildrenById, findFolders } from '@/apifox2/helpers'
import type { ApiDetails } from '@/apifox2/types'
import { useTabContentContext } from '@/apifox2/composables/useTabContent'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

interface DataSource extends ApiDetails {
  groupPath?: string
}

const menuStore = useApifox2MenuStore()
const { tabData } = useTabContentContext()

const dataSource = computed<DataSource[]>(() => {
  const menuRawList = menuStore.menuRawList
  if (!menuRawList) return []

  return findChildrenById(menuRawList, tabData.key)
    .filter((it) => it.type === MenuItemType.ApiDetail)
    .map((item) => {
      const groupPath = item.parentId
        ? findFolders(menuRawList, [], item.parentId)
            .map((it) => it.name)
            .join(' / ')
        : undefined
      return { ...(item.data as ApiDetails), groupPath }
    })
})
</script>

<style scoped>
.a2-fal-method {
  font-size: 12px;
  font-weight: 600;
}
</style>

<template>
  <div class="a2-recycle">
    <el-tabs v-model="activeKey" class="a2-recycle-tabs">
      <el-tab-pane label="接口" :name="CatalogType.Http" />
      <el-tab-pane label="数据模型" :name="CatalogType.Schema" />
      <el-tab-pane label="快捷请求" :name="CatalogType.Request" />
    </el-tabs>

    <div class="a2-recycle-body">
      <el-table :data="tableData" row-key="id" class="a2-recycle-table" :border="true">
        <el-table-column type="selection" width="40" />
        <el-table-column label="文件名称">
          <template #default="{ row }">
            <div class="a2-recycle-name">
              <HttpMethodText
                v-if="isHttp(row.deletedItem)"
                class="a2-recycle-method"
                :method="row.deletedItem.data?.method"
              />
              <FileIcon
                v-else
                :type="row.deletedItem.type"
                :size="15"
                :style="{ color: hasAccentColor(row.deletedItem.type) ? accentColor : undefined }"
              />
              <span>{{ row.deletedItem.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作人" width="150">
          <template #default="{ row }">
            <el-tooltip :content="row.creator.username" placement="top">
              <span>{{ row.creator.name }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="剩余时间" width="150" prop="expiredAt" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-popconfirm title="确定恢复该文件？" placement="left" @confirm="restore(row.id)">
              <template #reference>
                <el-button size="small" link type="primary">恢复</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import FileIcon from '@/apifox2/components/icons/FileIcon.vue'
import HttpMethodText from '@/apifox2/components/icons/HttpMethodText.vue'
import { API_MENU_CONFIG } from '@/apifox2/configs/static'
import { CatalogType, MenuItemType } from '@/apifox2/enums'
import { hasAccentColor } from '@/apifox2/helpers'
import type { ApiMenuData } from '@/apifox2/components/ApiMenu'
import type { RecycleCatalogType } from '@/apifox2/types'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

const menuStore = useApifox2MenuStore()
const activeKey = ref<RecycleCatalogType>(CatalogType.Http)

const tableData = computed(() => menuStore.recyleRawData?.[activeKey.value].list ?? [])
const accentColor = computed(() => API_MENU_CONFIG[activeKey.value].accentColor)

function isHttp(item: ApiMenuData): boolean {
  return item.type === MenuItemType.ApiDetail || item.type === MenuItemType.HttpRequest
}

function restore(restoreId: string) {
  menuStore.restoreMenuItem({ restoreId, catalogType: activeKey.value })
}
</script>

<style scoped>
.a2-recycle {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.a2-recycle-tabs {
  padding: 0 16px;
}

.a2-recycle-body {
  padding: 16px;
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.a2-recycle-name {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.a2-recycle-method {
  font-size: 12px;
  font-weight: bold;
}
</style>

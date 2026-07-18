<template>
  <div class="a2-blank">
    <div class="a2-blank-grid">
      <div
        v-for="item in items"
        :key="item.catalogType"
        class="a2-blank-card"
        @click="item.onClick()"
      >
        <div class="a2-blank-card-icon">
          <FileIcon :type="item.catalogType" :size="35" :style="{ color: item.accentColor }" />
        </div>
        <div class="a2-blank-card-label">{{ item.label }}</div>
      </div>
    </div>

    <el-dropdown trigger="click" placement="bottom" @command="onMoreCommand">
      <button class="a2-blank-more">
        <span>更多功能</span>
        <ChevronDownIcon :size="14" />
      </button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item command="newFolder">
            <FolderPlusIcon :size="18" class="a2-blank-more-icon" /> 新建接口目录
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup lang="ts">
import { ChevronDownIcon, FolderPlusIcon } from 'lucide-vue-next'
import FileIcon from '@/apifox2/components/icons/FileIcon.vue'
import { API_MENU_CONFIG } from '@/apifox2/configs/static'
import { CatalogType, MenuItemType } from '@/apifox2/enums'
import { useHelpers } from '@/apifox2/composables/useHelpers'
import { useTabContentContext } from '@/apifox2/composables/useTabContent'
import { useApifox2NewCatalog } from '@/apifox2/composables/useModals'

const { createApiDetails, createApiRequest, createDoc, createApiSchema } = useHelpers()
const { tabData } = useTabContentContext()
const { openNewCatalog } = useApifox2NewCatalog()

const items = [
  {
    catalogType: CatalogType.Http,
    label: '新建接口',
    accentColor: API_MENU_CONFIG[CatalogType.Http].accentColor,
    onClick: () => createApiDetails({}, { replaceTab: tabData.key }),
  },
  {
    catalogType: CatalogType.Request,
    label: '快捷请求',
    accentColor: API_MENU_CONFIG[CatalogType.Request].accentColor,
    onClick: () => createApiRequest({}, { replaceTab: tabData.key }),
  },
  {
    catalogType: CatalogType.Markdown,
    label: '新建 Markdown',
    accentColor: API_MENU_CONFIG[CatalogType.Markdown].accentColor,
    onClick: () => createDoc({}, { replaceTab: tabData.key }),
  },
  {
    catalogType: CatalogType.Schema,
    label: '新建数据模型',
    accentColor: API_MENU_CONFIG[CatalogType.Schema].accentColor,
    onClick: () => createApiSchema({}, { replaceTab: tabData.key }),
  },
]

function onMoreCommand(command: string) {
  if (command === 'newFolder') {
    openNewCatalog({ type: MenuItemType.ApiDetailFolder })
  }
}
</script>

<style scoped>
.a2-blank {
  display: flex;
  height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 0;
}

.a2-blank-grid {
  display: grid;
  grid-template-columns: repeat(4, 168px);
  gap: 16px;
  margin-bottom: 24px;
}

@media (max-width: 900px) {
  .a2-blank-grid {
    grid-template-columns: repeat(2, 168px);
  }
}

.a2-blank-card {
  cursor: pointer;
  background-color: var(--a2-color-fill-tertiary);
  border: 1px solid var(--a2-color-border-secondary);
  border-radius: 8px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.a2-blank-card:hover {
  border-color: var(--a2-color-primary);
}

.a2-blank-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 64px 20px;
}

.a2-blank-card-label {
  padding: 16px 8px;
  text-align: center;
  background-color: var(--a2-color-fill-tertiary);
}

.a2-blank-more {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--a2-color-text-tertiary);
  font-size: 14px;
}

.a2-blank-more-icon {
  margin-right: 6px;
}
</style>

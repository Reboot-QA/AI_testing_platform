<template>
  <PanelLayout layout-name="接口管理" @open-settings="emit('open-settings', $event)">
    <template #left>
      <div class="a2-menu-toolbar">
        <InputSearch />

        <el-tooltip content="显示筛选条件" placement="top">
          <button class="a2-tool-btn">
            <FilterIcon :size="16" />
          </button>
        </el-tooltip>

        <el-dropdown trigger="click" @command="onCreate">
          <button class="a2-tool-btn primary">
            <PlusIcon :size="18" />
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="opt in createOptions" :key="opt.type" :command="opt.type">
                <FileIcon :type="opt.type" :size="16" class="a2-create-icon" />
                {{ opt.label }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div class="a2-menu-scroll">
        <ApiMenu />
      </div>
    </template>

    <template #right>
      <ApiTab />
    </template>
  </PanelLayout>
</template>

<script setup lang="ts">
import { FilterIcon, PlusIcon } from 'lucide-vue-next'
import PanelLayout from '@/apifox2/components/layout/PanelLayout.vue'
import InputSearch from '@/apifox2/components/InputSearch.vue'
import ApiMenu from '@/apifox2/components/ApiMenu/ApiMenu.vue'
import ApiTab from '@/apifox2/components/ApiTab/ApiTab.vue'
import FileIcon from '@/apifox2/components/icons/FileIcon.vue'
import { MenuItemType } from '@/apifox2/enums'
import { useHelpers } from '@/apifox2/composables/useHelpers'

const emit = defineEmits<{ 'open-settings': [string] }>()

const { createTabItem } = useHelpers()

// 对应 home/page.tsx 的新建下拉：接口 / 快捷请求 / Markdown / 数据模型
const createOptions: { type: MenuItemType; label: string }[] = [
  { type: MenuItemType.ApiDetail, label: '新建接口' },
  { type: MenuItemType.HttpRequest, label: '新建快捷请求' },
  { type: MenuItemType.Doc, label: '新建 Markdown' },
  { type: MenuItemType.ApiSchema, label: '新建数据模型' },
]

function onCreate(type: MenuItemType) {
  createTabItem(type)
}
</script>

<style scoped>
.a2-menu-toolbar {
  display: flex;
  gap: 4px;
  padding: 8px;
  align-items: center;
}

.a2-tool-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  padding: 0 8px;
  border: 1px solid var(--a2-color-border-secondary);
  border-radius: 6px;
  background: var(--a2-color-bg-container);
  color: var(--a2-color-text-secondary);
  cursor: pointer;
  flex-shrink: 0;
}

.a2-tool-btn:hover {
  color: var(--a2-color-primary);
  border-color: var(--a2-color-primary);
}

.a2-tool-btn.primary {
  background: var(--a2-color-primary);
  border-color: var(--a2-color-primary);
  color: #fff;
}

.a2-tool-btn.primary:hover {
  color: #fff;
  opacity: 0.9;
}

.a2-menu-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.a2-create-icon {
  margin-right: 6px;
  color: var(--a2-color-primary);
}
</style>

<template>
  <div class="a2-apitab">
    <div class="a2-tab-bar">
      <VueDraggable
        v-model="tabStore.tabItems"
        :animation="150"
        filter=".a2-tab-close"
        :prevent-on-filter="false"
        class="a2-tab-list"
      >
        <el-dropdown
          v-for="item in tabStore.tabItems"
          :key="item.key"
          trigger="contextmenu"
          @command="onContextCommand"
        >
          <div
            class="a2-tab"
            :class="{ active: item.key === tabStore.activeTabKey }"
            @click="tabStore.activeTabItem({ key: item.key })"
          >
            <ApiTabLabel :menu-data="menuDataOf(item.key)" :tab-item="item" />
            <span
              class="a2-tab-close"
              :class="{ changed: item.data?.editStatus === 'changed' }"
              @click.stop="handleClose(item.key)"
            >
              <XIcon :size="15" />
            </span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="closeAll">关闭所有标签页</el-dropdown-item>
              <el-dropdown-item command="closeOthers">关闭其他标签页</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </VueDraggable>

      <div class="a2-tab-actions">
        <button class="a2-tab-act-btn" title="新建" @click="addBlank">
          <PlusIcon :size="16" />
        </button>
        <el-dropdown trigger="click" @command="onContextCommand">
          <button class="a2-tab-act-btn">
            <MoreHorizontalIcon :size="16" />
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="closeAll">关闭所有标签页</el-dropdown-item>
              <el-dropdown-item command="closeOthers">关闭其他标签页</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="a2-tab-content">
      <template v-for="item in tabStore.tabItems" :key="item.key">
        <div v-if="item.key === tabStore.activeTabKey" class="a2-tab-content-item">
          <ApiTabPane :tab="item" />
        </div>
      </template>
      <el-empty v-if="!tabStore.tabItems.length" description="没有打开的页签" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { VueDraggable } from 'vue-draggable-plus'
import { ElMessageBox } from 'element-plus'
import { MoreHorizontalIcon, PlusIcon, XIcon } from 'lucide-vue-next'
import ApiTabLabel from './ApiTabLabel.vue'
import ApiTabPane from './ApiTabPane.vue'
import { nanoid } from '@/apifox2/lib/nanoid'
import { useApifox2TabStore } from '@/apifox2/stores/menuTab'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

const tabStore = useApifox2TabStore()
const menuStore = useApifox2MenuStore()

function menuDataOf(key: string) {
  return menuStore.menuRawList?.find((it) => it.id === key)
}

function handleClose(key: string) {
  const item = tabStore.getTabItem({ key })
  if (item?.data?.editStatus === 'changed') {
    ElMessageBox.confirm('有修改的内容未保存！', '', {
      confirmButtonText: '确认关闭',
      cancelButtonText: '取消',
      type: 'warning',
    })
      .then(() => tabStore.removeTabItem({ key }))
      .catch(() => {})
  } else {
    tabStore.removeTabItem({ key })
  }
}

function addBlank() {
  tabStore.addTabItem({ key: nanoid(6), label: '新建...', contentType: 'blank' })
}

function onContextCommand(command: string) {
  if (command === 'closeAll') {
    tabStore.removeAllTabItems()
  } else if (command === 'closeOthers') {
    tabStore.removeOtherTabItems()
  }
}
</script>

<style scoped>
.a2-apitab {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.a2-tab-bar {
  display: flex;
  align-items: center;
  height: 40px;
  padding: 8px 12px 0 8px;
  flex-shrink: 0;
  overflow: hidden;
}

.a2-tab-list {
  display: flex;
  align-items: center;
  gap: 2px;
  overflow-x: auto;
  flex: 1;
  min-width: 0;
}

.a2-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 8px 0 10px;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  color: var(--a2-color-text-secondary);
  font-size: 13px;
}

.a2-tab:hover {
  background-color: var(--a2-color-fill-tertiary);
}

.a2-tab:hover .a2-tab-close {
  opacity: 1;
}

.a2-tab.active {
  color: var(--a2-color-primary);
  background-color: var(--a2-color-fill-secondary);
}

.a2-tab-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  border-radius: 50%;
  transition: opacity 0.15s;
}

.a2-tab-close.changed {
  opacity: 1;
  position: relative;
}

.a2-tab-close:hover {
  background-color: var(--a2-color-fill-secondary);
}

.a2-tab-actions {
  display: flex;
  gap: 4px;
  margin-left: 8px;
  flex-shrink: 0;
}

.a2-tab-act-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  color: var(--a2-color-text-secondary);
}

.a2-tab-act-btn:hover {
  background-color: var(--a2-color-fill-tertiary);
}

.a2-tab-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.a2-tab-content-item {
  height: 100%;
}
</style>

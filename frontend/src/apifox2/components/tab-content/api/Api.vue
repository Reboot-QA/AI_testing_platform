<template>
  <div class="a2-api">
    <!-- 新建态：直接进入编辑 -->
    <div v-if="isCreating" class="a2-api-full">
      <ApiDocEditing />
    </div>

    <!-- 已存在：文档 / 修改文档 双 Tab + 侧栏 -->
    <div v-else class="a2-api-existing">
      <div class="a2-api-main">
        <el-tabs v-model="activeTab" class="a2-api-tabs">
          <el-tab-pane label="文档" name="doc">
            <div class="a2-api-pane"><ApiDoc /></div>
          </el-tab-pane>
          <el-tab-pane label="修改文档" name="docEdit">
            <div class="a2-api-pane"><ApiDocEditing /></div>
          </el-tab-pane>
        </el-tabs>

        <el-tooltip content="历史记录、SEO 设置" placement="top-start">
          <button
            class="a2-api-panelbtn"
            :class="{ active: panelOpen }"
            @click="panelOpen = !panelOpen"
          >
            <PanelRightIcon :size="18" />
          </button>
        </el-tooltip>
      </div>

      <ApiSidePanel :open="panelOpen" @close="panelOpen = false" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { PanelRightIcon } from 'lucide-vue-next'
import ApiDoc from './ApiDoc.vue'
import ApiDocEditing from './ApiDocEditing.vue'
import ApiSidePanel from './ApiSidePanel.vue'
import { PageTabStatus } from '@/apifox2/components/ApiTab/ApiTab.enum'
import { useTabContentContext } from '@/apifox2/composables/useTabContent'

const { tabData } = useTabContentContext()

const isCreating = tabData.data?.tabStatus === PageTabStatus.Create
const activeTab = ref('docEdit')
const panelOpen = ref(false)
</script>

<style scoped>
.a2-api {
  height: 100%;
  overflow: hidden;
}

.a2-api-full,
.a2-api-existing {
  height: 100%;
}

.a2-api-existing {
  display: flex;
  overflow: hidden;
}

.a2-api-main {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.a2-api-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.a2-api-tabs :deep(.el-tabs__header) {
  padding: 0 16px;
  margin-bottom: 0;
}

.a2-api-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.a2-api-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.a2-api-pane {
  height: 100%;
  overflow: hidden;
}

.a2-api-panelbtn {
  position: absolute;
  top: 6px;
  right: 12px;
  z-index: 5;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--a2-color-text-secondary);
  padding: 4px;
  border-radius: 4px;
  display: inline-flex;
}

.a2-api-panelbtn.active {
  background-color: var(--a2-color-fill-secondary);
}
</style>

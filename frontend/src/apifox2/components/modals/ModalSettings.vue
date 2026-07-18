<template>
  <el-dialog
    v-model="visible"
    width="950px"
    :show-close="false"
    append-to-body
    class="a2-settings-dialog"
  >
    <div class="a2-settings-layout">
      <div class="a2-settings-side">
        <div class="a2-settings-side-title">设置</div>
        <div class="a2-settings-menu">
          <div
            v-for="item in menuItems"
            :key="item.key"
            class="a2-settings-menu-item"
            :class="{ active: selectedKey === item.key }"
            @click="selectedKey = item.key"
          >
            <component :is="item.icon" :size="16" />
            <span>{{ item.label }}</span>
          </div>
        </div>
      </div>

      <div class="a2-settings-content">
        <div class="a2-settings-content-title">{{ activeItem?.label }}</div>
        <ThemeEditor v-if="selectedKey === 'appearance'" />
        <Viewer v-else :value="aboutContent" :plugins="viewerPlugins" />
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { Viewer } from '@bytemd/vue-next'
import gfm from '@bytemd/plugin-gfm'
import 'bytemd/dist/index.css'
import { InfoIcon, ShirtIcon } from 'lucide-vue-next'
import ThemeEditor from '@/apifox2/components/ThemeEditor/ThemeEditor.vue'
import { useApifox2Modals } from '@/apifox2/composables/useModals'

const { state } = useApifox2Modals()

const viewerPlugins = [gfm()]

const menuItems = [
  { key: 'appearance', label: '外观', icon: ShirtIcon },
  { key: 'about', label: '关于此项目', icon: InfoIcon },
]

const visible = computed({
  get: () => state.settings.visible,
  set: (v) => {
    state.settings.visible = v
  },
})

const selectedKey = computed({
  get: () => state.settings.selectedKey ?? 'appearance',
  set: (v) => {
    state.settings.selectedKey = v
  },
})

const activeItem = computed(() => menuItems.find((it) => it.key === selectedKey.value))

watch(
  () => state.settings.visible,
  (v) => {
    if (v && !state.settings.selectedKey) state.settings.selectedKey = 'appearance'
  },
)

const aboutContent =
  '## 介绍\n\n这是一个精心仿制 Apifox 界面的纯前端项目，使用 Next + Antd + TypeScript + TailwindCSS 开发，源码融入了很多好的编码实践，能让你学习到如何组织和建设一个复杂的 React 项目，非常适合 React 新手学习！\n\n## 动机\n\n在日常工作中，我经常会使用 Antd 来构建页面，但大多数页面的结构和交互都是比较简单的。为了精进对 Next + Antd 的使用技巧，我选择了 Apifox 这个相对复杂的界面进行模仿，希望在实践中能够掌握使用 Antd 打造出高级的页面效果。\n\n可能有很多小伙伴也抱有类似的学习动机，所以我将代码开源出来，希望能帮助各位，感兴趣的话不妨到点个 star⭐ 收藏一下噢~'
</script>

<style scoped>
.a2-settings-layout {
  display: flex;
  min-height: 480px;
}

.a2-settings-side {
  width: 256px;
  flex-shrink: 0;
  padding: 16px 0;
  background-color: var(--a2-color-fill-tertiary);
}

.a2-settings-side-title {
  font-size: 18px;
  padding: 0 16px 16px;
}

.a2-settings-menu {
  padding: 0 16px;
}

.a2-settings-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--a2-color-text-secondary);
}

.a2-settings-menu-item:hover {
  color: var(--a2-color-primary);
}

.a2-settings-menu-item.active {
  background-color: var(--a2-color-fill-secondary);
  color: var(--a2-color-text);
}

.a2-settings-content {
  flex: 1;
  padding: 16px;
  overflow: auto;
}

.a2-settings-content-title {
  font-size: 18px;
  padding-bottom: 16px;
}
</style>

<style>
.a2-settings-dialog .el-dialog__header {
  display: none;
}

.a2-settings-dialog .el-dialog__body {
  padding: 0;
}
</style>

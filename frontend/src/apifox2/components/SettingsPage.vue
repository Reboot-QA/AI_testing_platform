<template>
  <PanelLayout layout-name="项目设置" @open-settings="emit('open-settings', $event)">
    <template #left>
      <div class="a2-set-menu">
        <div class="a2-set-group">
          <div class="a2-set-group-title"><SettingsIcon :size="16" /> 通用设置</div>
          <div class="a2-set-item">基本设置</div>
          <div class="a2-set-item">功能设置</div>
          <div class="a2-set-subitem">接口功能设置</div>
          <div class="a2-set-subitem">高级设置</div>
        </div>

        <div class="a2-set-group">
          <div class="a2-set-group-title"><LayersIcon :size="16" /> 项目资源</div>
          <div class="a2-set-item">常用参数</div>
          <div class="a2-set-item">公共响应</div>
        </div>
      </div>
    </template>

    <template #right>
      <div class="a2-set-right">
        待实现的设置页
        <el-skeleton :rows="5" animated />
        <el-skeleton :rows="5" animated />
      </div>
    </template>
  </PanelLayout>
</template>

<script setup lang="ts">
import { LayersIcon, SettingsIcon } from 'lucide-vue-next'
import PanelLayout from '@/apifox2/components/layout/PanelLayout.vue'

const emit = defineEmits<{ 'open-settings': [string] }>()
</script>

<style scoped>
.a2-set-menu {
  padding: 8px;
}

.a2-set-group {
  margin-bottom: 12px;
}

.a2-set-group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  color: var(--a2-color-text-tertiary);
  font-size: 13px;
}

.a2-set-item {
  padding: 6px 8px 6px 32px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--a2-color-text-secondary);
}

.a2-set-item:hover {
  background-color: var(--a2-color-fill-tertiary);
}

.a2-set-subitem {
  padding: 6px 8px 6px 48px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--a2-color-text-secondary);
  font-size: 13px;
}

.a2-set-subitem:hover {
  background-color: var(--a2-color-fill-tertiary);
}

.a2-set-right {
  padding: 20px;
}
</style>

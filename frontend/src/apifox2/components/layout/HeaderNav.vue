<template>
  <div class="a2-header">
    <div class="a2-header-right">
      <button class="a2-hbtn" title="设置" @click="emit('open-settings', 'appearance')">
        <SettingsIcon :size="14" />
      </button>

      <el-dropdown trigger="click" @command="onCommand">
        <button class="a2-hbtn">
          <span class="a2-logo-mini"><IconLogo /></span>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="about">
              <InfoIcon :size="16" class="a2-menu-icon" /> 关于项目
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { InfoIcon, SettingsIcon } from 'lucide-vue-next'
import IconLogo from '@/apifox2/components/icons/IconLogo.vue'

const emit = defineEmits<{ 'open-settings': [string] }>()

function onCommand(command: string) {
  if (command === 'about') {
    emit('open-settings', 'about')
  }
}
</script>

<style scoped>
.a2-header {
  display: flex;
  height: 100%;
  align-items: center;
}

.a2-header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.a2-hbtn {
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
  transition: background-color 0.2s;
}

.a2-hbtn:hover {
  background-color: var(--a2-color-fill-tertiary);
}

.a2-logo-mini {
  display: inline-flex;
  width: 16px;
  height: 16px;
  align-items: center;
  justify-content: center;
}

.a2-logo-mini :deep(svg) {
  width: 100%;
  height: 100%;
}

.a2-menu-icon {
  margin-right: 4px;
}
</style>

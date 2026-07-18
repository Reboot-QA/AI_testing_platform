<template>
  <div class="a2-side-panel" :class="{ open }">
    <div class="a2-sp-main">
      <div class="a2-sp-head">
        <span class="a2-sp-title">历史记录</span>
        <button class="a2-sp-close" @click="emit('close')">
          <XIcon :size="16" />
        </button>
      </div>
      <div class="a2-sp-body">
        <el-skeleton :rows="4" animated />
        <el-skeleton :rows="4" animated />
      </div>
    </div>

    <div class="a2-sp-rail">
      <button class="a2-sp-rail-btn"><HistoryIcon :size="16" /></button>
      <button class="a2-sp-rail-btn"><Settings2Icon :size="16" /></button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { HistoryIcon, Settings2Icon, XIcon } from 'lucide-vue-next'

defineProps<{ open?: boolean }>()
const emit = defineEmits<{ close: [] }>()
</script>

<style scoped>
.a2-side-panel {
  height: 100%;
  overflow: hidden;
  display: none;
  border-left: 1px solid var(--a2-color-border-secondary);
}

.a2-side-panel.open {
  display: flex;
}

.a2-sp-main {
  width: 320px;
}

.a2-sp-head {
  display: flex;
  height: 50px;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid var(--a2-color-border-secondary);
}

.a2-sp-title {
  font-size: 16px;
  font-weight: 500;
}

.a2-sp-close {
  margin-left: auto;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--a2-color-text-secondary);
  display: inline-flex;
}

.a2-sp-body {
  padding: 16px;
}

.a2-sp-rail {
  height: 100%;
  padding: 8px 4px;
  border-left: 1px solid var(--a2-color-border-secondary);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.a2-sp-rail-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--a2-color-text-secondary);
  display: inline-flex;
  padding: 4px;
}
</style>

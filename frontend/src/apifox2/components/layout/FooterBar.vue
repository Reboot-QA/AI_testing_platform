<template>
  <div class="a2-footer">
    <button v-if="isSideMenuCollapsed" class="a2-fbtn" @click="expand">
      <ArrowRightToLineIcon :size="14" />
    </button>
    <button v-else class="a2-fbtn" @click="collapse">
      <ArrowLeftToLineIcon :size="14" />
    </button>

    <div class="a2-footer-right">
      <button class="a2-fbtn" title="外观" @click="emit('open-settings', 'appearance')">
        <ShirtIcon :size="14" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeftToLineIcon, ArrowRightToLineIcon, ShirtIcon } from 'lucide-vue-next'
import { useApifox2Layout } from '@/apifox2/composables/layout'

const emit = defineEmits<{ 'open-settings': [string] }>()

const { isSideMenuCollapsed, collapse, expand } = useApifox2Layout()
</script>

<style scoped>
.a2-footer {
  display: flex;
  height: 100%;
  align-items: center;
  padding-left: 12px;
  padding-right: 24px;
}

.a2-footer-right {
  margin-left: auto;
  display: flex;
  align-items: center;
}

.a2-fbtn {
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

.a2-fbtn:hover {
  background-color: var(--a2-color-fill-tertiary);
}
</style>

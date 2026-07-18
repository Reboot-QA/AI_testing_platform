<template>
  <div ref="groupRef" class="a2-panel-group">
    <template v-if="!isSideMenuCollapsed">
      <div class="a2-side-panel" :style="{ width: sideWidth + 'px' }">
        <div class="a2-side-title">
          <span class="a2-side-title-text">{{ layoutName }}</span>
        </div>
        <slot name="left" />
      </div>

      <div class="a2-resize-handle" :class="{ dragging }" @pointerdown="startDrag">
        <div class="a2-resize-handle-inner" />
      </div>
    </template>

    <div class="a2-main-panel">
      <div class="a2-main-content">
        <slot name="right" />
      </div>
      <div class="a2-footer-wrap">
        <FooterBar @open-settings="emit('open-settings', $event)" />
      </div>
    </div>

    <div v-if="isSideMenuCollapsed" class="a2-expand-trigger" @click="expand">
      <ChevronRightIcon :size="12" :stroke-width="3" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { ChevronRightIcon } from 'lucide-vue-next'
import FooterBar from './FooterBar.vue'
import { useApifox2Layout } from '@/apifox2/composables/layout'

defineProps<{ layoutName?: string }>()
const emit = defineEmits<{ 'open-settings': [string] }>()

const SIDE_DEFAULT = 280
const SIDE_MIN = 200
const SIDE_MAX = 600

const groupRef = ref<HTMLElement | null>(null)
const sideWidth = ref(SIDE_DEFAULT)
const dragging = ref(false)

const { isSideMenuCollapsed, expand, registerPanelControls } = useApifox2Layout()

registerPanelControls({
  collapse: () => {
    isSideMenuCollapsed.value = true
  },
  expand: () => {
    isSideMenuCollapsed.value = false
  },
})

let startX = 0
let startWidth = 0

function onMove(e: PointerEvent) {
  const delta = e.clientX - startX
  const next = Math.min(SIDE_MAX, Math.max(SIDE_MIN, startWidth + delta))
  sideWidth.value = next
}

function endDrag() {
  dragging.value = false
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', endDrag)
}

function startDrag(e: PointerEvent) {
  dragging.value = true
  startX = e.clientX
  startWidth = sideWidth.value
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', endDrag)
}

onBeforeUnmount(endDrag)
</script>

<style scoped>
.a2-panel-group {
  position: relative;
  display: flex;
  height: 100%;
  width: 100%;
}

.a2-side-panel {
  display: flex;
  height: 100%;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

.a2-side-title {
  padding: 8px;
}

.a2-side-title-text {
  padding: 0 8px;
  font-size: 18px;
  font-weight: 600;
}

.a2-resize-handle {
  position: relative;
  flex-basis: 1px;
  flex-shrink: 0;
  cursor: col-resize;
}

.a2-resize-handle-inner {
  height: 100%;
  width: 1px;
  background-color: var(--a2-color-border-secondary);
  transition: background-color 0.15s;
}

.a2-resize-handle:hover .a2-resize-handle-inner,
.a2-resize-handle.dragging .a2-resize-handle-inner {
  background-color: var(--a2-color-primary);
}

.a2-main-panel {
  position: relative;
  display: flex;
  height: 100%;
  flex: 1;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
  min-width: 0;
}

.a2-main-content {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.a2-footer-wrap {
  flex-shrink: 0;
  flex-basis: 36px;
  height: 36px;
  border-top: 1px solid var(--a2-color-border-secondary);
}

.a2-expand-trigger {
  position: absolute;
  left: 0;
  top: 50%;
  z-index: 50;
  display: flex;
  height: 48px;
  width: 16px;
  transform: translateY(-50%);
  cursor: pointer;
  align-items: center;
  justify-content: center;
  border-top-right-radius: 8px;
  border-bottom-right-radius: 8px;
  color: var(--a2-color-primary);
  background-color: var(--a2-color-fill-alter);
  box-shadow: 1px 0 4px rgba(16, 24, 40, 0.08);
}

.a2-expand-trigger:hover {
  background-color: var(--a2-color-fill-secondary);
}
</style>

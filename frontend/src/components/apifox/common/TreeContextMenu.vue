<template>
  <teleport to="body">
    <ul
      v-if="visible"
      ref="menuRef"
      class="tree-ctx"
      :style="{ left: posX + 'px', top: posY + 'px' }"
      @click.stop
    >
      <template v-for="it in items" :key="it.key">
        <li v-if="it.divided" class="divider" role="separator" />
        <li
          :class="{
            danger: it.danger,
            disabled: it.disabled,
            'has-children': !!it.children?.length,
            active: openSubKey === it.key,
          }"
          @click="onItemClick(it)"
          @mouseenter="(e) => onItemEnter(it, e)"
        >
          <span v-if="it.icon" class="ico" :class="it.icon">
            <template v-if="it.icon === 'http'">HTTP</template>
            <el-icon v-else-if="it.icon === 'folder'"><FolderAdd /></el-icon>
            <el-icon v-else-if="it.icon === 'rename'"><EditPen /></el-icon>
            <el-icon v-else-if="it.icon === 'copy'"><CopyDocument /></el-icon>
            <el-icon v-else-if="it.icon === 'delete'"><Delete /></el-icon>
            <el-icon v-else-if="it.icon === 'import'"><Download /></el-icon>
            <el-icon v-else-if="it.icon === 'case'"><DocumentAdd /></el-icon>
            <el-icon v-else-if="it.icon === 'curl'"><Link /></el-icon>
            <el-icon v-else-if="it.icon === 'more'"><MoreFilled /></el-icon>
          </span>
          <span class="label">{{ it.label }}</span>
          <span v-if="it.shortcut" class="shortcut">{{ it.shortcut }}</span>
          <el-icon v-else-if="it.children?.length" class="arrow"><ArrowRight /></el-icon>
        </li>
      </template>
    </ul>

    <ul
      v-if="visible && subItems.length"
      ref="subMenuRef"
      class="tree-ctx sub"
      :style="{ left: subPosX + 'px', top: subPosY + 'px' }"
      @click.stop
    >
      <li v-for="sub in subItems" :key="sub.key" @click="pick(sub.key)">
        <span class="label">{{ sub.label }}</span>
      </li>
    </ul>
  </teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { TreeContextMenuItem } from '@/types/apifox'

const VIEWPORT_MARGIN = 8

const props = withDefaults(
  defineProps<{
    visible?: boolean
    x?: number
    y?: number
    items?: TreeContextMenuItem[]
  }>(),
  {
    visible: false,
    x: 0,
    y: 0,
    items: () => [],
  },
)
const emit = defineEmits<{
  select: [key: string]
  close: []
}>()

const menuRef = ref<HTMLElement | null>(null)
const subMenuRef = ref<HTMLElement | null>(null)
const posX = ref(0)
const posY = ref(0)
const openSubKey = ref('')
const subItems = ref<TreeContextMenuItem[]>([])
const subPosX = ref(0)
const subPosY = ref(0)

function clampToViewport(el: HTMLElement, x: number, y: number, flipUp = false) {
  const rect = el.getBoundingClientRect()
  let nextX = x
  let nextY = y
  if (flipUp && rect.bottom > window.innerHeight - VIEWPORT_MARGIN) {
    nextY = y - rect.height - 4
  }
  if (nextY + rect.height > window.innerHeight - VIEWPORT_MARGIN) {
    nextY = Math.max(VIEWPORT_MARGIN, window.innerHeight - rect.height - VIEWPORT_MARGIN)
  }
  if (nextY < VIEWPORT_MARGIN) nextY = VIEWPORT_MARGIN
  if (nextX + rect.width > window.innerWidth - VIEWPORT_MARGIN) {
    nextX = window.innerWidth - rect.width - VIEWPORT_MARGIN
  }
  nextX = Math.max(VIEWPORT_MARGIN, nextX)
  return { x: nextX, y: nextY }
}

async function repositionMenu(flipUp = false) {
  posX.value = props.x
  posY.value = props.y
  await nextTick()
  const el = menuRef.value
  if (!el) return
  const next = clampToViewport(el, props.x, props.y, flipUp)
  posX.value = next.x
  posY.value = next.y
}

async function repositionSubMenu(x: number, y: number) {
  subPosX.value = x
  subPosY.value = y
  await nextTick()
  const el = subMenuRef.value
  if (!el) return
  const next = clampToViewport(el, x, y)
  subPosX.value = next.x
  subPosY.value = next.y
}

function pick(key: string) {
  emit('select', key)
  emit('close')
  resetSub()
}

function resetSub() {
  openSubKey.value = ''
  subItems.value = []
}

function onItemClick(it: TreeContextMenuItem) {
  if (it.disabled) return
  if (it.children?.length) return
  pick(it.key)
}

function onItemEnter(it: TreeContextMenuItem, e: MouseEvent) {
  if (!it.children?.length) {
    resetSub()
    return
  }
  const el = e.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  openSubKey.value = it.key
  subItems.value = it.children
  repositionSubMenu(rect.right - 4, rect.top)
}

function onDocClick() {
  if (props.visible) {
    emit('close')
    resetSub()
  }
}

watch(
  () => [props.visible, props.x, props.y, props.items?.length] as const,
  ([visible]) => {
    if (!visible) return
    repositionMenu(true)
  },
)

watch(
  () => props.visible,
  (visible) => {
    if (!visible) resetSub()
    if (visible) document.addEventListener('click', onDocClick)
    else document.removeEventListener('click', onDocClick)
  },
)

onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.tree-ctx {
  position: fixed;
  z-index: 3000;
  min-width: 196px;
  max-height: calc(100vh - 16px);
  overflow-y: auto;
  margin: 0;
  padding: var(--ax-space-1) 0;
  list-style: none;
  background: var(--ax-bg);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-md, 8px);
  box-shadow: 0 8px 24px rgb(15 23 42 / 12%);
}

.tree-ctx.sub {
  min-width: 160px;
  z-index: 3001;
}

.tree-ctx li {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  min-height: 34px;
  padding: 0 var(--ax-space-3);
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text);
  cursor: pointer;
  user-select: none;
}

.tree-ctx li:hover:not(.divider):not(.disabled) {
  background: var(--ax-bg-hover);
}

.tree-ctx li.disabled {
  color: var(--ax-text-placeholder);
  cursor: not-allowed;
}

.tree-ctx li.danger {
  color: var(--ax-danger);
}

.tree-ctx li.divider {
  min-height: 0;
  height: 1px;
  margin: var(--ax-space-1) 0;
  padding: 0;
  background: var(--ax-border);
  cursor: default;
}

.ico {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  flex-shrink: 0;
  color: var(--ax-text-secondary);
}

.ico.http {
  width: auto;
  min-width: 30px;
  padding: 0 4px;
  border-radius: 3px;
  background: #fff7ed;
  color: #ea580c;
  font-size: 10px;
  font-weight: 700;
  line-height: 16px;
}

.label {
  flex: 1;
  min-width: 0;
}

.shortcut {
  flex-shrink: 0;
  font-size: var(--ax-font-xs);
  color: var(--ax-text-placeholder);
}

.arrow {
  flex-shrink: 0;
  color: var(--ax-text-placeholder);
  font-size: 12px;
}
</style>

<template>
  <div ref="wrapRef" class="add-step-wrap" :class="{ 'add-step-wrap--compact': compact }">
    <button
      type="button"
      class="add-step-btn"
      :class="{ 'add-step-btn--compact': compact }"
      @click.stop="toggle"
    >
      <el-icon v-if="!compact"><Plus /></el-icon>
      {{ label }}
    </button>

    <Teleport to="body">
      <Transition name="add-step-drop">
        <div
          v-if="open"
          ref="dropdownRef"
          class="add-step-dropdown"
          :class="{ 'add-step-dropdown--up': openUp }"
          :style="dropdownStyle"
        >
          <div class="add-step-panel">
            <section class="menu-section">
              <div class="section-title">请求接口</div>
              <button
                v-for="item in requestItems"
                :key="item.command"
                type="button"
                class="menu-item menu-item--row"
                :class="`menu-item--${item.tone}`"
                @click="pick(item.command)"
              >
                <span class="item-icon" :class="`item-icon--${item.tone}`">
                  <span v-if="item.iconText" class="item-icon-text">{{ item.iconText }}</span>
                  <el-icon v-else-if="item.icon"><component :is="item.icon" /></el-icon>
                </span>
                <span class="item-label">{{ item.label }}</span>
              </button>
            </section>

            <section class="menu-section">
              <div class="section-title">其他</div>
              <div class="menu-grid">
                <button
                  v-for="item in otherItems"
                  :key="item.command"
                  type="button"
                  class="menu-item menu-item--grid"
                  :class="`menu-item--${item.tone}`"
                  @click="pick(item.command)"
                >
                  <span class="item-icon" :class="`item-icon--${item.tone}`">
                    <el-icon><component :is="item.icon" /></el-icon>
                  </span>
                  <span class="item-label">{{ item.label }}</span>
                </button>
              </div>
            </section>

            <section class="menu-section">
              <div class="section-title">场景用例</div>
              <button
                v-for="item in scenarioItems"
                :key="item.command"
                type="button"
                class="menu-item menu-item--row"
                :class="`menu-item--${item.tone}`"
                @click="pick(item.command)"
              >
                <span class="item-icon" :class="`item-icon--${item.tone}`">
                  <el-icon><component :is="item.icon" /></el-icon>
                </span>
                <span class="item-label">{{ item.label }}</span>
              </button>
            </section>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue'
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import {
  Clock,
  Connection,
  Document,
  DocumentCopy,
  Folder,
  Link,
  Monitor,
  Plus,
  RefreshRight,
  Share,
  SetUp,
  Sort,
} from '@element-plus/icons-vue'

import type { ScenarioAddStepCommand } from '@/types/apifox'

type MenuTone =
  | 'purple'
  | 'yellow'
  | 'blue'
  | 'border'
  | 'green'
  | 'pink'
  | 'orange'
  | 'teal'
  | 'geekblue'
  | 'neutral'

interface MenuItemDef {
  command: ScenarioAddStepCommand
  label: string
  icon?: Component
  iconText?: string
  tone: MenuTone
}

// compact：容器（分组/条件/循环）内联入口，退化成一行文字链接，由外层虚线占位框承载「拖入或 添加步骤」
withDefaults(defineProps<{ compact?: boolean; label?: string }>(), {
  compact: false,
  label: '添加步骤',
})

const emit = defineEmits<{ command: [ScenarioAddStepCommand] }>()

const wrapRef = ref<HTMLElement | null>(null)
const dropdownRef = ref<HTMLElement | null>(null)
const open = ref(false)
const openUp = ref(false)
const dropdownStyle = ref<Record<string, string>>({})

const VIEWPORT_MARGIN = 8
const MENU_GAP = 8
const MENU_MIN_WIDTH = 360

const requestItems: MenuItemDef[] = [
  { command: 'import-endpoint', label: '从接口导入', icon: Connection, tone: 'purple' },
  { command: 'import-case', label: '从单接口用例导入', iconText: 'TC', tone: 'yellow' },
  { command: 'import-debug', label: '从接口调试用例导入', icon: Monitor, tone: 'blue' },
  { command: 'http', label: '添加 HTTP 请求', icon: Link, tone: 'border' },
  { command: 'import-curl', label: '从 cURL 导入', icon: DocumentCopy, tone: 'border' },
]

const otherItems: MenuItemDef[] = [
  { command: 'group', label: '分组', icon: Folder, tone: 'green' },
  { command: 'if', label: '条件分支', icon: Sort, tone: 'pink' },
  { command: 'loop', label: '循环', icon: RefreshRight, tone: 'orange' },
  { command: 'wait', label: '等待时间', icon: Clock, tone: 'teal' },
  { command: 'db', label: '数据库操作', icon: SetUp, tone: 'geekblue' },
  { command: 'break', label: '跳出循环', icon: Share, tone: 'orange' },
  { command: 'continue', label: '跳过本轮', icon: Share, tone: 'teal' },
]

const scenarioItems: MenuItemDef[] = [
  { command: 'case', label: '引用用例', icon: Document, tone: 'border' },
  { command: 'scenario', label: '引用子场景', icon: DocumentCopy, tone: 'border' },
]

function updateDropdownPosition() {
  const anchor = wrapRef.value
  const menu = dropdownRef.value
  if (!anchor || !menu) return

  const rect = anchor.getBoundingClientRect()
  const menuHeight = menu.offsetHeight
  const menuWidth = Math.max(rect.width, MENU_MIN_WIDTH)

  let top = rect.bottom + MENU_GAP
  let maxHeight: number | undefined

  const spaceBelow = window.innerHeight - rect.bottom - MENU_GAP - VIEWPORT_MARGIN
  const spaceAbove = rect.top - MENU_GAP - VIEWPORT_MARGIN
  const viewportMaxHeight = window.innerHeight - VIEWPORT_MARGIN * 2

  // 下方放不下且上方更宽裕 → 向上展开（Apifox：靠近底部时菜单往上弹）
  if (menuHeight > 0 && menuHeight > spaceBelow && spaceAbove >= spaceBelow) {
    top = rect.top - MENU_GAP - menuHeight
    openUp.value = true
  } else {
    openUp.value = false
  }

  // 纵向 clamp，保证整块菜单落在视口内
  if (menuHeight > viewportMaxHeight) {
    top = VIEWPORT_MARGIN
    maxHeight = viewportMaxHeight
    openUp.value = false
  } else {
    if (top + menuHeight > window.innerHeight - VIEWPORT_MARGIN) {
      top = window.innerHeight - menuHeight - VIEWPORT_MARGIN
    }
    if (top < VIEWPORT_MARGIN) {
      top = VIEWPORT_MARGIN
    }
  }

  let left = rect.left
  if (left + menuWidth > window.innerWidth - VIEWPORT_MARGIN) {
    left = window.innerWidth - menuWidth - VIEWPORT_MARGIN
  }
  left = Math.max(VIEWPORT_MARGIN, left)

  dropdownStyle.value = {
    position: 'fixed',
    top: `${top}px`,
    left: `${left}px`,
    width: `${menuWidth}px`,
    zIndex: '5000',
    ...(maxHeight != null ? { maxHeight: `${maxHeight}px`, overflowY: 'auto' } : {}),
  }
}

async function repositionDropdown() {
  updateDropdownPosition()
  await nextTick()
  updateDropdownPosition()
  requestAnimationFrame(() => updateDropdownPosition())
}

async function toggle() {
  open.value = !open.value
  if (open.value) {
    await nextTick()
    await repositionDropdown()
  }
}

function pick(command: ScenarioAddStepCommand) {
  open.value = false
  emit('command', command)
}

function onDocMouseDown(e: MouseEvent) {
  if (!open.value) return
  const anchor = wrapRef.value
  const panel = dropdownRef.value
  const target = e.target as Node
  if (anchor?.contains(target) || panel?.contains(target)) return
  open.value = false
}

function onViewportChange() {
  if (open.value) repositionDropdown()
}

onMounted(() => {
  document.addEventListener('mousedown', onDocMouseDown)
  window.addEventListener('resize', onViewportChange)
  window.addEventListener('scroll', onViewportChange, true)
})
onUnmounted(() => {
  document.removeEventListener('mousedown', onDocMouseDown)
  window.removeEventListener('resize', onViewportChange)
  window.removeEventListener('scroll', onViewportChange, true)
})
</script>

<style scoped>
.add-step-wrap {
  position: relative;
  margin-top: var(--ax-space-2);
}

.add-step-wrap--compact {
  display: inline-flex;
  margin-top: 0;
}

.add-step-dropdown {
  background: var(--ax-bg);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  box-shadow: var(--ax-shadow-lg);
  padding: var(--ax-space-3);
}

.add-step-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ax-space-1);
  width: 100%;
  padding: var(--ax-space-2) var(--ax-space-3);
  border: 1px dashed var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg);
  color: var(--ax-text-secondary);
  font-size: var(--ax-font-sm);
  line-height: var(--ax-leading-compact);
  cursor: pointer;
  transition:
    background var(--ax-transition),
    border-color var(--ax-transition),
    color var(--ax-transition);
}

.add-step-btn--compact {
  width: auto;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--color-blue-6);
  font-size: var(--ax-text-caption-size);
}

.add-step-btn:hover {
  background: var(--ax-bg-hover);
  border-color: var(--color-blue-6);
  color: var(--color-blue-6);
}

/* 放在通用 hover 之后：同权重靠顺序覆盖，紧凑态 hover 只加下划线 */
.add-step-btn--compact:hover {
  background: transparent;
  border-color: transparent;
  text-decoration: underline;
}

.add-step-panel {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
}

.menu-section {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-1-5);
}

.section-title {
  font-size: var(--ax-font-xs);
  font-weight: var(--ax-font-weight-medium);
  color: var(--ax-text-secondary);
  padding: 0 var(--ax-space-0-5);
}

.menu-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--ax-space-1-5);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  width: 100%;
  padding: var(--ax-space-2) var(--ax-space-2-5);
  border: 1px solid transparent;
  border-radius: var(--ax-radius);
  background: transparent;
  color: var(--ax-text);
  font-size: var(--ax-font-sm);
  line-height: var(--ax-leading-compact);
  text-align: left;
  cursor: pointer;
  transition:
    background var(--ax-transition),
    border-color var(--ax-transition);
}

.menu-item--row.menu-item--purple {
  background: var(--ax-tag-purple-bg);
  border-color: color-mix(in srgb, var(--color-purple-6) 12%, white);
}

.menu-item--row.menu-item--yellow {
  background: color-mix(in srgb, var(--color-yellow-6) 14%, white);
  border-color: color-mix(in srgb, var(--color-yellow-6) 22%, white);
}

.menu-item--row.menu-item--blue {
  background: var(--ax-tag-blue-bg);
  border-color: color-mix(in srgb, var(--color-blue-6) 14%, white);
}

.menu-item--row.menu-item--border,
.menu-item--grid {
  background: var(--ax-bg);
  border-color: var(--ax-border);
}

.menu-item--grid {
  flex-direction: row;
  min-height: 36px;
}

.menu-item:hover {
  background: var(--ax-bg-hover);
  border-color: color-mix(in srgb, var(--color-blue-6) 24%, var(--ax-border));
}

.menu-item--purple:hover {
  background: color-mix(in srgb, var(--ax-tag-purple-bg) 70%, var(--ax-bg-hover));
}

.menu-item--yellow:hover {
  background: color-mix(in srgb, var(--color-yellow-6) 18%, var(--ax-bg-hover));
}

.menu-item--blue:hover {
  background: color-mix(in srgb, var(--ax-tag-blue-bg) 70%, var(--ax-bg-hover));
}

.item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 14px;
}

.item-icon-text {
  font-size: 10px;
  font-weight: var(--ax-font-weight-bold);
  line-height: 1;
}

.item-icon--purple {
  color: var(--ax-tag-purple-fg);
  background: color-mix(in srgb, var(--color-purple-6) 18%, white);
}

.item-icon--yellow {
  color: color-mix(in srgb, var(--color-orange-6) 85%, black);
  background: color-mix(in srgb, var(--color-yellow-6) 55%, white);
}

.item-icon--blue {
  color: var(--ax-tag-blue-fg);
  background: color-mix(in srgb, var(--color-blue-6) 16%, white);
}

.item-icon--border {
  color: var(--ax-tag-neutral-fg);
  background: var(--ax-tag-neutral-bg);
  border-radius: var(--ax-radius-sm);
}

.item-icon--green {
  color: var(--ax-tag-green-fg);
  background: var(--ax-tag-green-bg);
  border-radius: var(--ax-radius-sm);
}

.item-icon--pink {
  color: var(--color-pink-6);
  background: color-mix(in srgb, var(--color-pink-6) 12%, white);
  border-radius: var(--ax-radius-sm);
}

.item-icon--orange {
  color: var(--ax-tag-orange-fg);
  background: var(--ax-tag-orange-bg);
  border-radius: var(--ax-radius-sm);
}

.item-icon--teal {
  color: var(--ax-tag-teal-fg);
  background: var(--ax-tag-teal-bg);
  border-radius: var(--ax-radius-sm);
}

.item-icon--geekblue {
  color: var(--color-geekblue-6);
  background: color-mix(in srgb, var(--color-geekblue-6) 12%, white);
  border-radius: var(--ax-radius-sm);
}

.item-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.add-step-drop-enter-active,
.add-step-drop-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.add-step-drop-enter-from,
.add-step-drop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.add-step-dropdown--up.add-step-drop-enter-from,
.add-step-dropdown--up.add-step-drop-leave-to {
  transform: translateY(4px);
}
</style>

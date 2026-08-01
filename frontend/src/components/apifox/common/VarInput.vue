<template>
  <div
    ref="wrapRef"
    class="var-input"
    :class="[`is-${size}`, { 'is-focus': focused, 'is-disabled': disabled }]"
  >
    <div ref="mirrorEl" class="vi-mirror">
      <span
        v-for="(segment, index) in highlightedSegments"
        :key="index"
        :class="segment.state ? ['vi-token', `vi-${segment.state}`] : undefined"
        :title="segment.title"
        >{{ segment.text }}</span
      >
    </div>
    <input
      ref="inputEl"
      class="vi-field"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :maxlength="maxlength"
      :title="fieldTitle"
      spellcheck="false"
      @input="onInput"
      @scroll="syncScroll"
      @focus="onFocus"
      @blur="onBlur"
      @click="scrollCaretIntoView"
      @keydown="onKeydown"
      @keyup="onKeyup"
    />

    <Teleport to="body">
      <div
        v-if="panelVisible && filteredVariables.length"
        class="variable-suggest-panel"
        :style="panelStyle"
        @mousedown.prevent
      >
        <div class="variable-suggest-list">
          <div
            v-for="(item, index) in filteredVariables"
            :key="item.name"
            class="variable-suggest-item"
            :class="{ active: index === activeIndex }"
            @mouseenter="activeIndex = index"
            @click="pickVariable(item)"
          >
            <span class="variable-name">{{ item.name }}</span>
            <span class="variable-scope">{{ item.scopeLabel }}</span>
          </div>
        </div>
        <div v-if="activeVariable" class="variable-suggest-detail">
          <div class="detail-row">
            <span class="detail-label">变量名</span>
            <span class="detail-value">{{ activeVariable.name }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">变量值</span>
            <span class="detail-value detail-value-mono">{{
              previewValue(activeVariable.value)
            }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">所属</span>
            <span class="detail-value">{{ activeVariable.scopeLabel }}</span>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { useEditorVariables } from '@/composables/useEditorVariables'
import { useResolvableVars } from '@/composables/useResolvableVars'
import { VALUE_MAX_LEN } from '@/constants/limits'
import type { EditorVariable } from '@/types/apifox'

const props = withDefaults(
  defineProps<{
    modelValue?: string | null
    placeholder?: string
    size?: 'small' | 'default'
    disabled?: boolean
    /** 输入长度上限，默认值类上限；调用方需要更短（如键名）时覆盖 */
    maxlength?: number
  }>(),
  {
    modelValue: '',
    placeholder: '',
    size: 'small',
    disabled: false,
    maxlength: VALUE_MAX_LEN,
  },
)
const emit = defineEmits<{ 'update:modelValue': [v: string]; change: [v: string] }>()

interface PanelStyle {
  top: string
  left: string
  width: string
}

interface TriggerInfo {
  start: number
  filter: string
}

const wrapRef = ref<HTMLElement | null>(null)
const inputEl = ref<HTMLInputElement>()
const mirrorEl = ref<HTMLElement>()
const focused = ref(false)
const resolvable = useResolvableVars()
const suggestVariables = useEditorVariables()

const panelVisible = ref(false)
const panelStyle = ref<PanelStyle>({ top: '0px', left: '0px', width: '420px' })
const filterText = ref('')
const activeIndex = ref(0)
const triggerStart = ref(-1)

const filteredVariables = computed(() => {
  const query = filterText.value.trim().toLowerCase()
  const list = suggestVariables.value
  if (!query) return list
  return list.filter((item) => item.name.toLowerCase().includes(query))
})

const activeVariable = computed(() => filteredVariables.value[activeIndex.value] || null)

/** 高亮/hover：优先编辑上下文（含用例变量），否则退回壳层可解析集合 */
function hitFor(name: string): { value: string; source: string } | null {
  const fromSuggest = suggestVariables.value.find((v) => v.name === name)
  if (fromSuggest) {
    return { value: String(fromSuggest.value ?? ''), source: fromSuggest.scopeLabel || '变量' }
  }
  const r = resolvable.value[name]
  return r ? { value: r.value, source: r.source } : null
}

interface HighlightSegment {
  text: string
  state?: 'ok' | 'bad'
  title?: string
}

const highlightedSegments = computed<HighlightSegment[]>(() => {
  const raw = props.modelValue ?? ''
  const re = /\{\{([^}]*)\}\}/g
  const segments: HighlightSegment[] = []
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(raw))) {
    if (m.index > last) segments.push({ text: raw.slice(last, m.index) })
    const name = m[1].trim()
    const hit = hitFor(name)
    if (hit) {
      const tip = `${m[0]} = ${hit.value || '(空)'}（${hit.source}）`
      segments.push({ text: m[0], state: 'ok', title: tip })
    } else {
      const tip = `${m[0]} 未解析`
      segments.push({ text: m[0], state: 'bad', title: tip })
    }
    last = m.index + m[0].length
  }
  if (last < raw.length) segments.push({ text: raw.slice(last) })
  return segments
})

const fieldTitle = computed(() => {
  const raw = props.modelValue ?? ''
  const seen = new Set<string>()
  const lines: string[] = []
  let m: RegExpExecArray | null
  const re = /\{\{([^}]*)\}\}/g
  while ((m = re.exec(raw))) {
    const name = m[1].trim()
    if (seen.has(name)) continue
    seen.add(name)
    const hit = hitFor(name)
    if (hit) lines.push(`${name} = ${hit.value || '(空)'}（${hit.source}）`)
    else lines.push(`${name} 未解析`)
  }
  return lines.join('\n')
})

function previewValue(value: unknown) {
  const text = String(value ?? '')
  return text.length > 120 ? `${text.slice(0, 120)}...` : text || '（空）'
}

function positionPanel() {
  const el = inputEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  panelStyle.value = {
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    width: `${Math.max(rect.width, 420)}px`,
  }
}

function detectTrigger(text: string, cursor: number): TriggerInfo | null {
  const before = text.slice(0, cursor)
  const doubleMatch = before.match(/\{\{([^}]*)$/)
  if (doubleMatch) {
    return {
      start: before.length - doubleMatch[0].length,
      filter: doubleMatch[1] || '',
    }
  }
  if (before.endsWith('{') && !before.endsWith('{{')) {
    return {
      start: before.length - 1,
      filter: '',
    }
  }
  return null
}

function syncTrigger() {
  const el = inputEl.value
  if (!el) {
    panelVisible.value = false
    return
  }
  const cursor = el.selectionStart ?? 0
  const trigger = detectTrigger(el.value ?? '', cursor)
  if (!trigger || !filteredVariables.value.length) {
    panelVisible.value = false
    return
  }
  triggerStart.value = trigger.start
  filterText.value = trigger.filter
  activeIndex.value = 0
  panelVisible.value = true
  positionPanel()
}

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
  syncScroll()
  nextTick(syncTrigger)
}

function onKeyup(event: KeyboardEvent) {
  if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
    scrollCaretIntoView()
  }
  syncTrigger()
}

function onFocus() {
  focused.value = true
  nextTick(syncTrigger)
}

function syncScroll() {
  if (mirrorEl.value && inputEl.value) mirrorEl.value.scrollLeft = inputEl.value.scrollLeft
}

function scrollCaretIntoView() {
  const el = inputEl.value
  if (!el) return
  const start = el.selectionStart ?? 0
  const end = el.selectionEnd ?? start
  // 镜像层 token 加粗会导致视觉宽度与 input 不一致，用临时 span 测 caret 位置
  const probe = document.createElement('span')
  probe.style.cssText = 'position:fixed;visibility:hidden;white-space:pre;font:inherit;padding:0'
  const cs = getComputedStyle(el)
  probe.style.font = cs.font
  probe.textContent = el.value.slice(0, end)
  document.body.appendChild(probe)
  const caretX = probe.offsetWidth
  document.body.removeChild(probe)
  const pad = parseFloat(cs.paddingLeft) || 0
  const visible = el.clientWidth - pad * 2
  if (caretX - el.scrollLeft > visible - 8) {
    el.scrollLeft = Math.max(0, caretX - visible + 24)
  } else if (caretX - el.scrollLeft < 8) {
    el.scrollLeft = Math.max(0, caretX - 24)
  }
  syncScroll()
}

function scrollActiveSuggestIntoView() {
  nextTick(() => {
    const panel = document.querySelector('.variable-suggest-panel .variable-suggest-item.active')
    panel?.scrollIntoView({ block: 'nearest' })
  })
}

function onBlur() {
  focused.value = false
  emit('change', inputEl.value?.value ?? '')
  window.setTimeout(() => {
    panelVisible.value = false
  }, 120)
}

function onKeydown(event: KeyboardEvent) {
  if (panelVisible.value && filteredVariables.value.length) {
    const last = filteredVariables.value.length - 1
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      activeIndex.value = Math.min(activeIndex.value + 1, last)
      scrollActiveSuggestIntoView()
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      activeIndex.value = Math.max(activeIndex.value - 1, 0)
      scrollActiveSuggestIntoView()
      return
    }
    if (event.key === 'Enter') {
      if (activeVariable.value) {
        event.preventDefault()
        pickVariable(activeVariable.value)
      }
      return
    }
    if (event.key === 'Escape') {
      panelVisible.value = false
      return
    }
  }
}

function pickVariable(item: EditorVariable) {
  const el = inputEl.value
  if (!el || triggerStart.value < 0) return
  const text = props.modelValue ?? ''
  const cursor = el.selectionStart ?? text.length
  const after = text.slice(cursor)
  const insertion = `{{${item.name}}}`
  const newValue = `${text.slice(0, triggerStart.value)}${insertion}${after}`
  emit('update:modelValue', newValue)
  panelVisible.value = false
  nextTick(() => {
    const nextEl = inputEl.value
    if (!nextEl) return
    const caret = triggerStart.value + insertion.length
    nextEl.focus()
    nextEl.setSelectionRange(caret, caret)
    scrollCaretIntoView()
  })
}

function handleViewportChange() {
  if (panelVisible.value) positionPanel()
}

window.addEventListener('scroll', handleViewportChange, true)
window.addEventListener('resize', handleViewportChange)

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleViewportChange, true)
  window.removeEventListener('resize', handleViewportChange)
})
</script>

<style scoped>
.var-input {
  position: relative;
  display: block;
  width: 100%;
  height: var(--ax-control-height-sm);
  background: var(--el-fill-color-blank, var(--ax-raw-hex-fff));
  border: 1px solid var(--el-border-color, var(--ax-raw-hex-dcdfe6));
  border-radius: var(--el-border-radius-base, 4px);
  box-sizing: border-box;
  overflow: hidden;
}
.var-input.is-default {
  height: var(--ax-control-height);
}
.var-input.is-focus {
  border-color: var(--el-color-primary, var(--ax-raw-hex-409eff));
}
.var-input.is-disabled {
  background: var(--el-fill-color-light, var(--ax-raw-hex-f5f7fa));
  cursor: not-allowed;
}

.vi-mirror,
.vi-field {
  position: absolute;
  inset: 0;
  padding: 0 var(--ax-space-3);
  line-height: calc(var(--ax-control-height-sm) - 2px);
  font-size: var(--ax-text-body-sm-size);
  font-family: Consolas, Monaco, 'Courier New', monospace;
  white-space: pre;
  box-sizing: border-box;
}
.is-default .vi-mirror,
.is-default .vi-field {
  line-height: calc(var(--ax-control-height) - 2px);
  font-size: var(--ax-text-body-size);
}

.vi-mirror {
  color: var(--el-text-color-regular, var(--ax-raw-hex-606266));
  pointer-events: none;
  overflow: hidden;
}
.vi-field {
  width: 100%;
  background: transparent;
  color: transparent;
  caret-color: var(--el-text-color-primary, var(--ax-raw-hex-303133));
  border: none;
  outline: none;
  overflow-x: auto;
}
.vi-field::placeholder {
  color: var(--el-text-color-placeholder, var(--ax-raw-hex-a8abb2));
}
.vi-field::-webkit-scrollbar {
  display: none;
}

:deep(.vi-token.vi-ok) {
  color: var(--el-color-primary, var(--ax-raw-hex-409eff));
}
:deep(.vi-token.vi-bad) {
  color: var(--el-text-color-regular, var(--ax-raw-hex-606266));
}

.variable-suggest-panel {
  position: fixed;
  z-index: 5000;
  display: flex;
  background: var(--ax-raw-hex-fff);
  border: 1px solid var(--ax-raw-hex-dcdfe6);
  border-radius: 6px;
  box-shadow: 0 8px 24px var(--ax-raw-rgba-0-0-0-0-12);
  overflow: hidden;
}

.variable-suggest-list {
  width: 220px;
  max-height: 260px;
  overflow: auto;
  border-right: 1px solid var(--ax-raw-hex-ebeef5);
}

.variable-suggest-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ax-space-2);
  padding: var(--ax-space-2) var(--ax-space-3);
  cursor: pointer;
}

.variable-suggest-item:hover,
.variable-suggest-item.active {
  background: var(--ax-raw-hex-ecf5ff);
}

.variable-name {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-raw-hex-303133);
  font-family: Consolas, Monaco, monospace;
}

.variable-scope {
  font-size: var(--ax-text-caption-size);
  color: var(--ax-raw-hex-909399);
  white-space: nowrap;
}

.variable-suggest-detail {
  flex: 1;
  min-width: 0;
  padding: var(--ax-space-2-5) var(--ax-space-3);
  background: var(--ax-raw-hex-fafafa);
}

.detail-row {
  display: flex;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
  font-size: var(--ax-text-caption-size);
}

.detail-row:last-child {
  margin-bottom: 0;
}

.detail-label {
  width: 42px;
  color: var(--ax-raw-hex-909399);
  flex-shrink: 0;
}

.detail-value {
  color: var(--ax-raw-hex-303133);
  word-break: break-all;
}

.detail-value-mono {
  font-family: Consolas, Monaco, monospace;
}
</style>

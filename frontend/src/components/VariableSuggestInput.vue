<template>
  <div ref="wrapRef" class="variable-suggest-input">
    <el-input
      ref="inputRef"
      :model-value="modelValue"
      :type="type"
      :rows="rows"
      :placeholder="placeholder"
      :size="size"
      :disabled="disabled"
      :show-password="showPassword"
      @update:model-value="onInput"
      @keydown="onKeydown"
      @keyup="onKeyup"
      @blur="onBlur"
      @focus="onFocus"
      @paste="(event) => emit('paste', event)"
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
            <span class="detail-value detail-value-mono">{{ previewValue(activeVariable.value) }}</span>
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

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  variables: { type: Array, default: () => [] },
  placeholder: { type: String, default: '' },
  size: { type: String, default: 'small' },
  type: { type: String, default: 'text' },
  rows: { type: Number, default: 3 },
  disabled: { type: Boolean, default: false },
  showPassword: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'blur', 'paste'])

const wrapRef = ref(null)
const inputRef = ref(null)
const panelVisible = ref(false)
const panelStyle = ref({ top: '0px', left: '0px', width: '420px' })
const filterText = ref('')
const activeIndex = ref(0)
const triggerStart = ref(-1)

const filteredVariables = computed(() => {
  const query = filterText.value.trim().toLowerCase()
  const list = props.variables || []
  if (!query) return list
  return list.filter((item) => item.name.toLowerCase().includes(query))
})

const activeVariable = computed(() => filteredVariables.value[activeIndex.value] || null)

watch(
  () => props.variables,
  () => {
    if (panelVisible.value) syncTrigger()
  },
  { deep: true }
)

function previewValue(value) {
  const text = String(value ?? '')
  return text.length > 120 ? `${text.slice(0, 120)}...` : text || '（空）'
}

function getInputEl() {
  const component = inputRef.value
  return component?.textarea || component?.input || null
}

function positionPanel() {
  const el = getInputEl()
  if (!el) return
  const rect = el.getBoundingClientRect()
  panelStyle.value = {
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    width: `${Math.max(rect.width, 420)}px`,
  }
}

function detectTrigger(text, cursor) {
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
  const el = getInputEl()
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

function onInput(value) {
  emit('update:modelValue', value)
  nextTick(syncTrigger)
}

function onKeyup() {
  syncTrigger()
}

function onFocus() {
  nextTick(syncTrigger)
}

function onBlur(event) {
  emit('blur', event)
  window.setTimeout(() => {
    panelVisible.value = false
  }, 120)
}

function onKeydown(event) {
  if (!panelVisible.value || !filteredVariables.value.length) return
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % filteredVariables.value.length
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    activeIndex.value =
      (activeIndex.value - 1 + filteredVariables.value.length) % filteredVariables.value.length
  } else if (event.key === 'Enter') {
    if (activeVariable.value) {
      event.preventDefault()
      pickVariable(activeVariable.value)
    }
  } else if (event.key === 'Escape') {
    panelVisible.value = false
  }
}

function pickVariable(item) {
  const el = getInputEl()
  if (!el || triggerStart.value < 0) return
  const text = props.modelValue ?? ''
  const cursor = el.selectionStart ?? text.length
  const after = text.slice(cursor)
  const insertion = `{{${item.name}}}`
  const newValue = `${text.slice(0, triggerStart.value)}${insertion}${after}`
  emit('update:modelValue', newValue)
  panelVisible.value = false
  nextTick(() => {
    const nextEl = getInputEl()
    if (!nextEl) return
    const caret = triggerStart.value + insertion.length
    nextEl.focus()
    nextEl.setSelectionRange(caret, caret)
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
.variable-suggest-input {
  width: 100%;
}

.variable-suggest-panel {
  position: fixed;
  z-index: 5000;
  display: flex;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  overflow: hidden;
}

.variable-suggest-list {
  width: 220px;
  max-height: 260px;
  overflow: auto;
  border-right: 1px solid #ebeef5;
}

.variable-suggest-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
}

.variable-suggest-item:hover,
.variable-suggest-item.active {
  background: #ecf5ff;
}

.variable-name {
  font-size: 13px;
  color: #303133;
  font-family: Consolas, Monaco, monospace;
}

.variable-scope {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.variable-suggest-detail {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  background: #fafafa;
}

.detail-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}

.detail-row:last-child {
  margin-bottom: 0;
}

.detail-label {
  width: 42px;
  color: #909399;
  flex-shrink: 0;
}

.detail-value {
  color: #303133;
  word-break: break-all;
}

.detail-value-mono {
  font-family: Consolas, Monaco, monospace;
}
</style>

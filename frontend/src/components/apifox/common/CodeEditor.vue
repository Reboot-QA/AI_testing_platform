<template>
  <div class="code-editor" :style="{ height }">
    <div v-if="!readonly && showToolbar" class="toolbar">
      <el-button v-if="language === 'json'" link size="small" @click="format">格式化</el-button>
      <slot name="toolbar" />
    </div>
    <div class="editor-host">
      <vue-monaco-editor
        v-if="ready"
        :value="modelValue"
        :language="language"
        :theme="theme"
        :options="mergedOptions"
        @update:value="onChange"
        @mount="onMount"
      />
      <div v-else class="loading">加载编辑器…</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeMount, ref, shallowRef } from 'vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { ensureMonaco } from '@/plugins/monaco'

const props = defineProps({
  modelValue: { type: String, default: '' },
  language: { type: String, default: 'json' },
  height: { type: String, default: '240px' },
  readonly: { type: Boolean, default: false },
  theme: { type: String, default: 'vs' },
  showToolbar: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue'])

const ready = ref(false)
const editorRef = shallowRef(null)

const mergedOptions = computed(() => ({
  readOnly: props.readonly,
  minimap: { enabled: false },
  fontSize: 13,
  fontFamily: 'Consolas, Monaco, monospace',
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 2,
  lineNumbersMinChars: 3,
  overviewRulerLanes: 0,
  scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
}))

onBeforeMount(async () => {
  await ensureMonaco()
  ready.value = true
})

function onChange(value) {
  emit('update:modelValue', value ?? '')
}

function onMount(editor) {
  editorRef.value = editor
}

function format() {
  editorRef.value?.getAction('editor.action.formatDocument')?.run()
}

defineExpose({ format })
</script>

<style scoped>
.code-editor {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 8px;
  border-bottom: 1px solid var(--ax-border);
  background: var(--ax-bg-hover);
}

.editor-host {
  flex: 1;
  min-height: 0;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--ax-text-placeholder);
  font-size: 13px;
}
</style>

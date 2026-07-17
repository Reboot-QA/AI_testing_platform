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

<script setup lang="ts">
import { computed, onBeforeMount, ref, shallowRef } from 'vue'
import type { editor } from 'monaco-editor'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { ensureMonaco } from '@/plugins/monaco'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    language?: string
    height?: string
    readonly?: boolean
    theme?: string
    showToolbar?: boolean
  }>(),
  {
    modelValue: '',
    language: 'json',
    height: '240px',
    readonly: false,
    theme: 'vs',
    showToolbar: true,
  },
)
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const ready = ref(false)
const editorRef = shallowRef<editor.IStandaloneCodeEditor | null>(null)

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

function onChange(value: string | undefined) {
  emit('update:modelValue', value ?? '')
}

function onMount(ed: editor.IStandaloneCodeEditor) {
  editorRef.value = ed
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

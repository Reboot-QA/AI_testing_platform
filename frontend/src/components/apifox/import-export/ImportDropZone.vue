<template>
  <div
    class="drop-zone"
    :class="{ 'is-dragover': dragOver }"
    @click="pickFile"
    @dragover.prevent="dragOver = true"
    @dragleave.prevent="dragOver = false"
    @drop.prevent="onDrop"
  >
    <input ref="inputRef" type="file" class="drop-zone-input" :accept="accept" @change="onInput" />
    <el-icon class="drop-zone-icon" :size="40"><UploadFilled /></el-icon>
    <p class="drop-zone-text">
      <template v-if="variant === 'postman'">
        拖拽文件到此处或选择
        <button type="button" class="drop-zone-link" @click.stop="pickFile">文件</button>
        或
        <button type="button" class="drop-zone-link" @click.stop="onFolder">文件夹</button>
      </template>
      <template v-else>点击或拖拽文件到本区域导入</template>
    </p>
    <p v-if="fileName" class="drop-zone-file">已选择：{{ fileName }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

withDefaults(
  defineProps<{
    accept?: string
    variant?: 'default' | 'postman'
  }>(),
  { accept: '.json,.yaml,.yml,.txt,*', variant: 'default' },
)

const emit = defineEmits<{ file: [file: File]; folder: [] }>()

const inputRef = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)
const fileName = ref('')

function pickFile() {
  inputRef.value?.click()
}

function onFolder() {
  emit('folder')
  ElMessage.info('敬请期待')
}

function takeFile(file: File | undefined) {
  if (!file) return
  fileName.value = file.name
  emit('file', file)
}

function onInput(e: Event) {
  const input = e.target as HTMLInputElement
  takeFile(input.files?.[0])
  input.value = ''
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  takeFile(e.dataTransfer?.files?.[0])
}

function clear() {
  fileName.value = ''
}

defineExpose({ clear })
</script>

<style scoped>
.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ax-space-2);
  min-height: 180px;
  padding: var(--ax-space-5);
  border: 1px dashed var(--ax-border);
  border-radius: var(--ax-radius);
  background: var(--ax-bg-subtle);
  cursor: pointer;
  transition:
    border-color var(--ax-transition),
    background var(--ax-transition);
}

.drop-zone:hover,
.drop-zone.is-dragover {
  border-color: var(--ax-brand);
  background: var(--ax-tag-blue-bg);
}

.drop-zone-input {
  display: none;
}

.drop-zone-icon {
  color: var(--ax-text-secondary);
}

.drop-zone-text {
  margin: 0;
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
  text-align: center;
}

.drop-zone-link {
  padding: 0;
  border: none;
  background: none;
  color: var(--ax-brand);
  cursor: pointer;
  font-size: inherit;
}

.drop-zone-file {
  margin: 0;
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text);
}
</style>

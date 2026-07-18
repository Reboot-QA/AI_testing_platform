<template>
  <div class="a2-inputdesc">
    <el-input
      type="textarea"
      :rows="3"
      placeholder="支持 Markdown 格式"
      :model-value="modelValue"
      @update:model-value="emit('update:modelValue', $event)"
    />
    <div class="a2-inputdesc-expand">
      <button class="a2-inputdesc-btn" @click="openModal">
        <Maximize2Icon :size="12" />
      </button>
    </div>

    <el-dialog
      v-model="open"
      title="接口说明"
      width="1200px"
      :close-on-click-modal="false"
      append-to-body
    >
      <div class="a2-inputdesc-editor">
        <MarkdownEditor :value="editorValue" @change="editorValue = $event" />
      </div>
      <template #footer>
        <el-button @click="open = false">取消</el-button>
        <el-button type="primary" @click="save">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Maximize2Icon } from 'lucide-vue-next'
import MarkdownEditor from '@/apifox2/components/MarkdownEditor.vue'

const props = defineProps<{ modelValue?: string }>()
const emit = defineEmits<{ 'update:modelValue': [string] }>()

const open = ref(false)
const editorValue = ref('')

function openModal() {
  editorValue.value = props.modelValue ?? ''
  open.value = true
}

function save() {
  open.value = false
  emit('update:modelValue', editorValue.value)
}
</script>

<style scoped>
.a2-inputdesc {
  position: relative;
}

.a2-inputdesc-expand {
  position: absolute;
  right: 4px;
  top: 4px;
  z-index: 5;
}

.a2-inputdesc-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--a2-color-text-secondary);
  display: inline-flex;
  padding: 2px;
}

.a2-inputdesc-editor {
  height: calc(100vh - 340px);
  overflow: hidden;
  border: 1px solid var(--a2-color-border-secondary);
  border-radius: 6px;
}
</style>

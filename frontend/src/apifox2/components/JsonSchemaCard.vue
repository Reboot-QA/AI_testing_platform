<template>
  <div>
    <div class="a2-jsc-card">
      <div class="a2-jsc-toolbar">
        <UIBtn primary class="a2-jsc-inline" @click="jsonModalOpen = true">
          <ScanTextIcon :size="14" />
          <span class="a2-jsc-ml">通过 JSON 生成</span>
        </UIBtn>

        <div class="a2-jsc-right">
          <UIBtn @click="schemaModalOpen = true">
            <span class="a2-jsc-inline a2-jsc-gap"> <BracesIcon :size="12" /> JSON Schema </span>
          </UIBtn>
        </div>
      </div>

      <div class="a2-jsc-body">
        <JsonSchemaEditor
          :value="value"
          :default-expand-all="editorProps?.defaultExpandAll"
          :read-only="editorProps?.readOnly"
          @change="onChange"
        />
      </div>
    </div>

    <!-- 通过 JSON 生成 -->
    <el-dialog
      v-model="jsonModalOpen"
      title="JSON Schema"
      width="800px"
      :close-on-click-modal="false"
      append-to-body
      @open="jsonStr = JSON.stringify(value, null, 2)"
    >
      <div class="a2-jsc-modal-box">
        <div class="a2-jsc-modal-head">输入 JSON</div>
        <MonacoEditor language="json" :value="jsonStr" height="350px" @change="jsonStr = $event" />
      </div>
      <template #footer>
        <el-button @click="jsonModalOpen = false">取消</el-button>
        <el-button type="primary" @click="jsonModalOpen = false">保存</el-button>
      </template>
    </el-dialog>

    <!-- JSON Schema 源码 -->
    <el-dialog
      v-model="schemaModalOpen"
      title="JSON Schema"
      width="800px"
      :close-on-click-modal="false"
      append-to-body
      @open="schemaStr = JSON.stringify(value, null, 2)"
    >
      <div class="a2-jsc-modal-box">
        <div class="a2-jsc-modal-head a2-jsc-end">
          <UIBtn @click="copySchema">
            <span class="a2-jsc-inline a2-jsc-gap"> <CopyIcon :size="12" /> 复制代码 </span>
          </UIBtn>
        </div>
        <MonacoEditor
          language="json"
          :value="schemaStr"
          height="350px"
          @change="schemaStr = $event"
        />
      </div>
      <template #footer>
        <el-button @click="schemaModalOpen = false">取消</el-button>
        <el-button type="primary" @click="saveSchema">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { BracesIcon, CopyIcon, ScanTextIcon } from 'lucide-vue-next'
import UIBtn from '@/apifox2/components/UIBtn.vue'
import MonacoEditor from '@/apifox2/components/MonacoEditor/MonacoEditor.vue'
import JsonSchemaEditor from '@/apifox2/json-schema/JsonSchemaEditor.vue'
import type { JsonSchema } from '@/apifox2/json-schema'

const props = defineProps<{
  value?: JsonSchema
  editorProps?: { defaultExpandAll?: boolean; readOnly?: boolean }
}>()
const emit = defineEmits<{ change: [JsonSchema | undefined] }>()

const jsonModalOpen = ref(false)
const schemaModalOpen = ref(false)
const jsonStr = ref<string>()
const schemaStr = ref<string>()

function onChange(v: JsonSchema | undefined) {
  emit('change', v)
}

function copySchema() {
  void navigator.clipboard.writeText(JSON.stringify(props.value, null, 2)).then(() => {
    ElMessage.success('已复制')
  })
}

function saveSchema() {
  if (schemaStr.value) {
    try {
      emit('change', JSON.parse(schemaStr.value) as JsonSchema)
      schemaModalOpen.value = false
    } catch (err) {
      if (err instanceof SyntaxError) {
        ElMessage.error('JSON Schema 格式校验不通过，请检查！')
      }
    }
  }
}
</script>

<style scoped>
.a2-jsc-card {
  border: 1px solid var(--a2-color-border-secondary);
  border-radius: 6px;
  margin-bottom: 12px;
}

.a2-jsc-toolbar {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--a2-color-border-secondary);
}

.a2-jsc-inline {
  display: inline-flex;
  align-items: center;
}

.a2-jsc-gap {
  gap: 4px;
}

.a2-jsc-ml {
  margin-left: 4px;
}

.a2-jsc-right {
  margin-left: auto;
}

.a2-jsc-body {
  padding: 12px;
}

.a2-jsc-modal-box {
  border-radius: 6px;
  border: 1px solid var(--a2-color-border-secondary);
  overflow: hidden;
}

.a2-jsc-modal-head {
  padding: 4px 12px;
  border-bottom: 1px solid var(--a2-color-border-secondary);
}

.a2-jsc-end {
  display: flex;
  justify-content: flex-end;
}
</style>

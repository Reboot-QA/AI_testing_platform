<template>
  <el-dialog
    :model-value="open"
    title="添加响应"
    width="520px"
    append-to-body
    @update:model-value="emit('update:open', $event)"
  >
    <el-form label-position="top">
      <el-form-item label="名称" required>
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="HTTP 状态码" required>
        <el-select v-model="form.code" style="width: 100%">
          <el-option
            v-for="o in httpCodeOptions"
            :key="o.value"
            :label="o.label"
            :value="o.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="内容格式">
        <el-select v-model="form.contentType" style="width: 100%">
          <el-option
            v-for="o in contentTypeOptions"
            :key="o.value"
            :label="o.label"
            :value="o.value"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:open', false)">取消</el-button>
      <el-button type="primary" @click="onOk">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { contentTypeOptions, httpCodeOptions } from './options'
import { SchemaType } from '@/apifox2/json-schema'
import { ContentType } from '@/apifox2/enums'
import type { ApiDetailsResponse } from '@/apifox2/types'

type FormData = Pick<ApiDetailsResponse, 'name' | 'code' | 'contentType' | 'jsonSchema'>

const props = defineProps<{ open?: boolean }>()
const emit = defineEmits<{ 'update:open': [boolean]; finish: [FormData] }>()

function initial(): FormData {
  return {
    name: '成功',
    code: 200,
    contentType: ContentType.JSON,
    jsonSchema: { type: SchemaType.Object, properties: [] },
  }
}

const form = reactive<FormData>(initial())

watch(
  () => props.open,
  (v) => {
    if (v) Object.assign(form, initial())
  },
)

function onOk() {
  emit('finish', { ...form })
}
</script>

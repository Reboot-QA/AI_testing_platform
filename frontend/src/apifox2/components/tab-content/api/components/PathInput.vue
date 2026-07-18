<template>
  <el-input
    class="a2-path-input"
    placeholder="接口路径，“/”起始"
    :model-value="modelValue"
    @input="onInput"
  />
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { nanoid } from '@/apifox2/lib/nanoid'
import { ParamType } from '@/apifox2/enums'
import type { Parameter } from '@/apifox2/types'

defineProps<{ modelValue?: string }>()
const emit = defineEmits<{
  'update:modelValue': [string | undefined]
  valueChange: [string | undefined]
  parseQueryParams: [Parameter[] | undefined]
}>()

let msgShown = false

function onInput(val: string) {
  emit('valueChange', val)

  if (val.endsWith('?')) {
    notify('Query 参数请在下方「请求参数」中填写')
    emit('update:modelValue', val.slice(0, val.length - 1))
    return
  }
  if (val.endsWith('#')) {
    notify('接口路径不支持填写 URL hash(#)')
    emit('update:modelValue', val.slice(0, val.length - 1))
    return
  }

  let finalVal = val
  const queryParams: Parameter[] = []
  try {
    const url = new URL(val.startsWith('http') ? val : `http://xxx.com/${val}`)
    url.searchParams.forEach((value, key) => {
      const dup = queryParams.find((p) => p.name === key)
      if (dup) {
        dup.type = ParamType.Array
        if (Array.isArray(dup.example)) {
          dup.example.push(value)
        } else {
          dup.example = typeof dup.example === 'string' ? [dup.example, value] : [value]
        }
      } else {
        queryParams.push({ id: nanoid(4), name: key, type: ParamType.String, example: value })
      }
    })
    if (queryParams.length > 0) {
      emit('parseQueryParams', queryParams)
    }
    finalVal = val.replace(url.search, '').replace(url.hash, '')
  } catch {
    // ignore
  }

  emit('update:modelValue', finalVal)
}

function notify(content: string) {
  if (msgShown) return
  msgShown = true
  ElMessage.info({ message: content, duration: 3, onClose: () => (msgShown = false) })
}
</script>

<style scoped>
.a2-path-input {
  flex: 1;
}
</style>

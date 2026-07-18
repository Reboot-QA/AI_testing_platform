<template>
  <el-cascader
    :model-value="internalValue"
    :options="catalogOptions"
    :props="cascaderProps"
    filterable
    :clearable="false"
    :placeholder="placeholder"
    style="width: 100%"
    @update:model-value="onChange"
  />
</template>

<script setup lang="ts">
import { computed, toRef } from 'vue'
import type { ApiMenuBase } from '@/apifox2/components/ApiMenu/ApiMenu.type'
import { ROOT_CATALOG } from '@/apifox2/configs/static'
import type { MenuItemType } from '@/apifox2/enums'
import { findFolders } from '@/apifox2/helpers'
import { useCatalog } from '@/apifox2/composables/useCatalog'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

const props = defineProps<{
  modelValue?: ApiMenuBase['parentId']
  type?: MenuItemType
  exclued?: string[]
  placeholder?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [string | undefined] }>()

const store = useApifox2MenuStore()
const { catalogOptions } = useCatalog({
  type: toRef(props, 'type'),
  exclued: toRef(props, 'exclued'),
})

const cascaderProps = { expandTrigger: 'hover' as const, checkStrictly: true }

const internalValue = computed<string[] | undefined>(() => {
  const value = props.modelValue
  if (store.menuRawList && value) {
    const group = findFolders(store.menuRawList, [], value).map(({ id }) => id)
    return group.length > 0 ? group : [ROOT_CATALOG]
  }
  return undefined
})

function onChange(val: unknown) {
  const arr = Array.isArray(val) ? val : []
  const lastOne = arr[arr.length - 1]
  if (typeof lastOne === 'string') {
    emit('update:modelValue', lastOne)
  }
}
</script>

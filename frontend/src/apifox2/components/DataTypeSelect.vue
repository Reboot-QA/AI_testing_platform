<template>
  <div v-if="type" class="a2-dts">
    <el-popover
      placement="right"
      trigger="click"
      :width="160"
      :disabled="disabled"
      popper-class="a2-dts-popover"
    >
      <template #reference>
        <span :class="{ 'a2-dts-select': !readOnly }" :style="{ color: `var(${typeColor})` }">
          {{ typeName }}
        </span>
      </template>
      <div class="a2-dts-menu">
        <div
          v-for="it in typeList"
          :key="it"
          class="a2-dts-menu-item"
          :class="{ active: it === type }"
          @click="onSelect(it)"
        >
          {{ schemaTypeText(it) }}
        </div>
      </div>
    </el-popover>

    <el-tooltip content="高级设置" placement="top">
      <span class="a2-dts-adv">
        <Settings2Icon :size="12" />
      </span>
    </el-tooltip>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Settings2Icon } from 'lucide-vue-next'
import { SchemaType, defaultSchemaTypeConfig } from '@/apifox2/json-schema/constants'
import { apiDirectoryData } from '@/apifox2/data/remote'

const props = defineProps<{
  type?: SchemaType
  disabled?: boolean
  readOnly?: boolean
  refId?: string
}>()
const emit = defineEmits<{ typeSelect: [SchemaType] }>()

const typeList: SchemaType[] = [
  SchemaType.Refer,
  SchemaType.String,
  SchemaType.Integer,
  SchemaType.Boolean,
  SchemaType.Object,
  SchemaType.Number,
  SchemaType.Null,
  SchemaType.Any,
]

function schemaTypeText(t: SchemaType) {
  return defaultSchemaTypeConfig[t].text
}

const typeName = computed(() => {
  if (props.type) {
    if (props.refId) {
      return apiDirectoryData.find((it) => it.id === props.refId)?.name
    }
    return defaultSchemaTypeConfig[props.type].text
  }
  return ''
})

const typeColor = computed(() => (props.type ? defaultSchemaTypeConfig[props.type].varColor : ''))

function onSelect(t: SchemaType) {
  emit('typeSelect', t)
}
</script>

<style scoped>
.a2-dts {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 8px;
}

.a2-dts-select {
  cursor: pointer;
}

.a2-dts-select:hover {
  text-decoration: underline;
}

.a2-dts-menu {
  padding: 4px 0;
}

.a2-dts-menu-item {
  height: 32px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  cursor: pointer;
  font-size: 13px;
}

.a2-dts-menu-item:hover {
  background-color: var(--a2-color-fill-tertiary);
}

.a2-dts-menu-item.active {
  color: var(--a2-color-primary);
}

.a2-dts-adv {
  display: none;
  align-items: center;
  padding: 2px;
  border-radius: 2px;
  cursor: pointer;
  opacity: 0.5;
  background-color: var(--a2-color-fill-tertiary);
}

.a2-dts-adv:hover {
  opacity: 1;
}
</style>

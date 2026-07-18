<template>
  <div>
    <div class="a2-body-types">
      <span
        v-for="t in types"
        :key="t.type"
        class="a2-body-tag"
        :class="{ checked: t.type === selectedType }"
        @click="selectType(t.type)"
      >
        {{ t.name }}
      </span>
    </div>

    <div>
      <div v-if="!value || value.type === BodyType.None" class="a2-body-none">
        该请求没有 Body 体
      </div>
      <ParamsEditableTable
        v-else-if="value.type === BodyType.FormData || value.type === BodyType.UrlEncoded"
        :value="value.parameters"
        @change="onParamsChange"
      />
      <JsonSchemaCard
        v-else-if="value.type === BodyType.Json || value.type === BodyType.Xml"
        :value="value.jsonSchema ?? defaultJsonSchema"
        @change="onJsonSchemaChange"
      />
      <span v-else>-</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ParamsEditableTable from '../components/ParamsEditableTable.vue'
import JsonSchemaCard from '@/apifox2/components/JsonSchemaCard.vue'
import { SchemaType } from '@/apifox2/json-schema'
import type { JsonSchema } from '@/apifox2/json-schema'
import { BodyType } from '@/apifox2/enums'
import type { ApiDetails, Parameter } from '@/apifox2/types'

const props = defineProps<{ value?: ApiDetails['requestBody'] }>()
const emit = defineEmits<{ change: [ApiDetails['requestBody']] }>()

const types = [
  { name: 'none', type: BodyType.None },
  { name: 'form-data', type: BodyType.FormData },
  { name: 'x-www-form-urlencoded', type: BodyType.UrlEncoded },
  { name: 'json', type: BodyType.Json },
  { name: 'xml', type: BodyType.Xml },
  { name: 'raw', type: BodyType.Raw },
  { name: 'binary', type: BodyType.Binary },
]

const defaultJsonSchema: JsonSchema = { type: SchemaType.Object, properties: [] }

const selectedType = computed(() => props.value?.type ?? BodyType.None)

function selectType(type: BodyType) {
  emit('change', { ...props.value, type })
}

function onParamsChange(parameters: Parameter[] | undefined) {
  emit('change', { ...props.value!, parameters })
}

function onJsonSchemaChange(jsonSchema: JsonSchema | undefined) {
  emit('change', { ...props.value!, jsonSchema })
}
</script>

<style scoped>
.a2-body-types {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px;
}

.a2-body-tag {
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  background-color: var(--a2-color-fill-tertiary);
  color: var(--a2-color-text-secondary);
}

.a2-body-tag.checked {
  background-color: rgba(255, 77, 79, 0.1);
  color: var(--a2-color-primary);
}

.a2-body-none {
  display: flex;
  height: 96px;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  color: var(--a2-color-text-tertiary);
  border: 1px solid var(--a2-color-fill-secondary);
}
</style>

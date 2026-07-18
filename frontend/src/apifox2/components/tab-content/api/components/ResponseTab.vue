<template>
  <div>
    <el-tabs v-model="activeResTabKey" type="card" class="a2-resp-tabs" @tab-remove="() => {}">
      <el-tab-pane
        v-for="(resp, idx) in value"
        :key="resp.id"
        :name="resp.id"
        :label="`${resp.name}(${resp.code})`"
      >
        <div class="a2-resp-pane">
          <div class="a2-resp-head">
            <div class="a2-resp-fields">
              <div class="a2-resp-field">
                <label>HTTP 状态码</label>
                <el-select
                  :model-value="resp.code"
                  style="width: 120px"
                  @change="updateResp(idx, { code: $event })"
                >
                  <el-option
                    v-for="o in httpCodeOptions"
                    :key="o.value"
                    :label="o.label"
                    :value="o.value"
                  />
                </el-select>
              </div>
              <div class="a2-resp-field">
                <label>名称</label>
                <el-input
                  :model-value="resp.name"
                  style="width: 88px"
                  @update:model-value="updateResp(idx, { name: $event })"
                />
              </div>
              <div class="a2-resp-field">
                <label>内容格式</label>
                <el-select
                  :model-value="resp.contentType"
                  style="width: 130px"
                  @change="updateResp(idx, { contentType: $event })"
                >
                  <el-option
                    v-for="o in contentTypeOptions"
                    :key="o.value"
                    :label="o.label"
                    :value="o.value"
                  />
                </el-select>
              </div>
              <div class="a2-resp-field">
                <label>Content-Type</label>
                <span>{{ getContentTypeString(resp.contentType as ContentType) }}</span>
              </div>
            </div>

            <div v-if="(value?.length ?? 0) > 1" class="a2-resp-del">
              <el-popconfirm
                title="确定删除？确定后点击右上角保存按钮生效"
                @confirm="removeResp(idx)"
              >
                <template #reference>
                  <el-button size="small" text><TrashIcon :size="14" /></el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>

          <JsonSchemaCard
            :value="resp.jsonSchema"
            :editor-props="{ defaultExpandAll: true }"
            @change="updateResp(idx, { jsonSchema: $event })"
          />

          <el-tabs v-if="examplesOf(resp.id).length > 0" type="card" class="a2-resp-examples">
            <el-tab-pane
              v-for="ex in examplesOf(resp.id)"
              :key="ex.id"
              :name="ex.id"
              :label="ex.name"
            >
              <div class="a2-resp-example-pane">
                <JsonViewer :value="ex.data" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-tab-pane>
    </el-tabs>

    <div class="a2-resp-add">
      <el-button text @click="modalOpen = true"> <PlusIcon :size="16" /> 添加 </el-button>
    </div>

    <ModalNewResponse v-model:open="modalOpen" @finish="onNewResponse" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { PlusIcon, TrashIcon } from 'lucide-vue-next'
import JsonSchemaCard from '@/apifox2/components/JsonSchemaCard.vue'
import JsonViewer from '@/apifox2/components/JsonViewer.vue'
import ModalNewResponse from '../ModalNewResponse.vue'
import { contentTypeOptions, httpCodeOptions } from '../options'
import { nanoid } from '@/apifox2/lib/nanoid'
import type { ContentType } from '@/apifox2/enums'
import { getContentTypeString } from '@/apifox2/helpers'
import type { ApiDetails, ApiDetailsResponse } from '@/apifox2/types'

const props = defineProps<{
  value?: ApiDetails['responses']
  responseExamples?: ApiDetails['responseExamples']
}>()
const emit = defineEmits<{ change: [ApiDetails['responses']] }>()

const activeResTabKey = ref<string | undefined>(props.value?.[0]?.id)
const modalOpen = ref(false)

function examplesOf(responseId: string) {
  return props.responseExamples?.filter((ex) => ex.responseId === responseId) ?? []
}

function updateResp(idx: number, patch: Partial<ApiDetailsResponse>) {
  emit(
    'change',
    props.value?.map((it, i) => (i === idx ? { ...it, ...patch } : it)),
  )
}

function removeResp(idx: number) {
  const newResponses = props.value?.filter((_, i) => i !== idx)
  emit('change', newResponses)
  activeResTabKey.value = newResponses?.[0]?.id
}

function onNewResponse(
  values: Pick<ApiDetailsResponse, 'name' | 'code' | 'contentType' | 'jsonSchema'>,
) {
  modalOpen.value = false
  const newResId = nanoid(6)
  emit('change', [...(props.value ?? []), { ...values, id: newResId } as ApiDetailsResponse])
  activeResTabKey.value = newResId
}
</script>

<style scoped>
.a2-resp-pane {
  padding: 16px;
}

.a2-resp-head {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.a2-resp-fields {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 24px;
}

.a2-resp-field {
  display: flex;
  align-items: center;
  gap: 6px;
}

.a2-resp-field label {
  color: var(--a2-color-text-secondary);
  font-size: 13px;
}

.a2-resp-del {
  margin-left: auto;
}

.a2-resp-add {
  margin-top: 4px;
}

.a2-resp-example-pane {
  padding: 16px;
}
</style>

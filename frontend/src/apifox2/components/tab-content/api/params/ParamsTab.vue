<template>
  <el-tabs v-model="activeKey" class="a2-params-tabs">
    <el-tab-pane name="params">
      <template #label>
        <span
          >Params<span v-if="paramsCount > 0" class="a2-badge">{{ paramsCount }}</span></span
        >
      </template>
      <div>
        <div class="a2-params-subtitle">Query 参数</div>
        <ParamsEditableTable :value="value?.query" @change="onQueryChange" />

        <template v-if="value?.path && value.path.length > 0">
          <div class="a2-params-subtitle">Path 参数</div>
          <ParamsEditableTable
            is-path-params-table
            :auto-new-row="false"
            :removable="false"
            :value="value.path"
            @change="onPathChange"
          />
        </template>
      </div>
    </el-tab-pane>

    <el-tab-pane label="Body" name="body">
      <ParamsBody :value="requestBody" @change="emit('bodyChange', $event)" />
    </el-tab-pane>

    <el-tab-pane label="Headers" name="headers">
      <div class="a2-params-pad">
        <ParamsEditableTable :value="value?.header" @change="onHeaderChange" />
      </div>
    </el-tab-pane>

    <el-tab-pane label="Cookie" name="cookie">
      <div class="a2-params-pad">
        <ParamsEditableTable :value="value?.cookie" @change="onCookieChange" />
      </div>
    </el-tab-pane>
  </el-tabs>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import ParamsEditableTable from '../components/ParamsEditableTable.vue'
import ParamsBody from './ParamsBody.vue'
import type { ApiDetails, Parameter } from '@/apifox2/types'

const props = defineProps<{
  value?: ApiDetails['parameters']
  requestBody?: ApiDetails['requestBody']
}>()
const emit = defineEmits<{
  change: [ApiDetails['parameters']]
  bodyChange: [ApiDetails['requestBody']]
}>()

const activeKey = ref('params')

const paramsCount = computed(
  () => (props.value?.query?.length ?? 0) + (props.value?.path?.length ?? 0),
)

function onQueryChange(query: Parameter[] | undefined) {
  emit('change', { ...props.value, query })
}
function onPathChange(path: Parameter[] | undefined) {
  emit('change', { ...props.value, path })
}
function onHeaderChange(header: Parameter[] | undefined) {
  emit('change', { ...props.value, header })
}
function onCookieChange(cookie: Parameter[] | undefined) {
  emit('change', { ...props.value, cookie })
}
</script>

<style scoped>
.a2-badge {
  margin-left: 4px;
  display: inline-flex;
  width: 16px;
  height: 16px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 12px;
  background-color: var(--a2-color-fill-secondary);
  color: var(--color-green-6, #4caf50);
}

.a2-params-subtitle {
  padding: 8px 0;
  color: var(--a2-color-text-tertiary);
  font-size: 13px;
}

.a2-params-pad {
  padding-top: 8px;
}
</style>

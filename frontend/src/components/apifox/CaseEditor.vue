<template>
  <div class="case-editor">
    <div class="row1">
      <el-input v-model="form.name" placeholder="用例名称" />
      <el-button type="primary" :loading="saving" @click="$emit('save')">保存</el-button>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="请求" name="request">
        <ApiEndpointEditor :form="form" :show-meta="false" :project-id="pid" />
      </el-tab-pane>
      <el-tab-pane label="用例变量" name="variables">
        <KvRowsEditor :rows="form.variables" />
      </el-tab-pane>
      <el-tab-pane label="前置操作" name="pre">
        <ProcessorsEditor :rows="form.pre_processors" phase="pre" :scripts="scripts" />
      </el-tab-pane>
      <el-tab-pane label="后置操作" name="post">
        <ProcessorsEditor
          :rows="form.post_processors"
          phase="post"
          :scripts="scripts"
          :allow-contract="false"
        />
      </el-tab-pane>
      <el-tab-pane label="数据驱动" name="data_drive">
        <DataDriveEditor :model="form.data_drive" :var-rows="form.variables" :datasets="datasets" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouteParamId } from '@/composables/useRouteParamId'
import type { Schemas } from '@/api/types'
import type { KvRow, RequestSpec } from '@/types/apifox'
import ApiEndpointEditor from '@/components/apifox/ApiEndpointEditor.vue'
import KvRowsEditor from '@/components/apifox/KvRowsEditor.vue'
import DataDriveEditor from '@/components/apifox/DataDriveEditor.vue'
import ProcessorsEditor from '@/components/apifox/ProcessorsEditor.vue'

type ScriptBrief = Schemas['ScriptBrief']
type DatasetBrief = Schemas['DatasetBrief']
type Processor = Schemas['ProcessorRow']

export interface CaseEditorForm {
  id?: number | null
  name: string
  category?: string
  request_spec: RequestSpec
  variables: KvRow[]
  assertions: Schemas['AssertionRow'][]
  extracts: Schemas['ExtractRow'][]
  pre_scripts: Schemas['CaseScriptOut'][]
  post_scripts: Schemas['CaseScriptOut'][]
  pre_processors: Processor[]
  post_processors: Processor[]
  data_drive: Schemas['DataDrive']
  version?: number
}

withDefaults(
  defineProps<{
    form: CaseEditorForm
    saving?: boolean
    scripts?: ScriptBrief[]
    datasets?: DatasetBrief[]
  }>(),
  {
    saving: false,
    scripts: () => [],
    datasets: () => [],
  },
)
defineEmits<{ save: [] }>()

const pid = useRouteParamId()
const activeTab = ref('request')
// 处理器由父组件加载用例后派生（deriveProcessors），本组件仅编辑 form.pre_processors/post_processors
</script>

<style scoped>
.row1 {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
</style>

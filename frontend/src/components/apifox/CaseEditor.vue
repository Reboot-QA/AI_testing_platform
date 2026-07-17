<template>
  <div class="case-editor">
    <div class="row1">
      <el-input v-model="form.name" placeholder="用例名称" />
      <el-button type="primary" :loading="saving" @click="$emit('save')">保存</el-button>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="请求" name="request">
        <ApiEndpointEditor :form="form" :show-meta="false" :project-id="route.params.projectId" />
      </el-tab-pane>
      <el-tab-pane label="用例变量" name="variables">
        <KvRowsEditor :rows="form.variables" />
      </el-tab-pane>
      <el-tab-pane label="前置" name="pre_scripts">
        <ScriptRefsEditor :rows="form.pre_scripts" :scripts="scripts" />
      </el-tab-pane>
      <el-tab-pane label="后置" name="post_scripts">
        <ScriptRefsEditor :rows="form.post_scripts" :scripts="scripts" />
      </el-tab-pane>
      <el-tab-pane label="断言" name="assertions">
        <AssertionsEditor :rows="form.assertions" />
      </el-tab-pane>
      <el-tab-pane label="提取" name="extracts">
        <ExtractsEditor :rows="form.extracts" />
      </el-tab-pane>
      <el-tab-pane label="数据驱动" name="data_drive">
        <DataDriveEditor :model="form.data_drive" :var-rows="form.variables" :datasets="datasets" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import type { Schemas } from '@/api/types'
import type { KvRow, RequestSpec } from '@/types/apifox'
import ApiEndpointEditor from '@/components/apifox/ApiEndpointEditor.vue'
import KvRowsEditor from '@/components/apifox/KvRowsEditor.vue'
import AssertionsEditor from '@/components/apifox/AssertionsEditor.vue'
import ExtractsEditor from '@/components/apifox/ExtractsEditor.vue'
import DataDriveEditor from '@/components/apifox/DataDriveEditor.vue'
import ScriptRefsEditor from '@/components/apifox/ScriptRefsEditor.vue'

type ScriptBrief = Schemas['ScriptBrief']
type DatasetBrief = Schemas['DatasetBrief']

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

const route = useRoute()
const activeTab = ref('request')
</script>

<style scoped>
.row1 {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
</style>

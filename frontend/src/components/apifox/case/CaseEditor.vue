<template>
  <div>
    <div class="mb-3 flex flex-wrap items-center gap-2">
      <el-input
        v-model="form.name"
        :maxlength="TITLE_MAX_LEN"
        placeholder="用例名称"
        class="min-w-0 flex-1 case-name-input"
      >
        <template v-if="listIndex != null" #prefix>
          <span class="case-list-index">{{ listIndex }}</span>
        </template>
      </el-input>
      <slot name="header-actions" />
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
        <ProcessorsEditor
          :rows="form.pre_processors"
          phase="pre"
          :scripts="scripts"
          :databases="databases"
          :sql-scripts="sqlScripts"
        />
      </el-tab-pane>
      <el-tab-pane label="后置操作" name="post">
        <ProcessorsEditor
          :rows="form.post_processors"
          phase="post"
          :scripts="scripts"
          :databases="databases"
          :sql-scripts="sqlScripts"
          :schemas="schemas"
          :allow-contract="allowContract"
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
import { TITLE_MAX_LEN } from '@/constants/limits'
import { useRouteParamId } from '@/composables/useRouteParamId'
import type { Schemas } from '@/api/types'
import type { CaseEditorForm } from '@/types/apifox'
import { provideEditorVariables } from '@/composables/useEditorVariables'
import ApiEndpointEditor from '@/components/apifox/endpoint/ApiEndpointEditor.vue'
import KvRowsEditor from '@/components/apifox/editors/KvRowsEditor.vue'
import DataDriveEditor from '@/components/apifox/editors/DataDriveEditor.vue'
import ProcessorsEditor from '@/components/apifox/editors/ProcessorsEditor.vue'
import { useEnvDatabases } from '@/composables/useEnvDatabases'
import { useSqlScripts } from '@/composables/useSqlScripts'

type ScriptBrief = Schemas['ScriptBrief']
type DatasetBrief = Schemas['DatasetBrief']

const props = withDefaults(
  defineProps<{
    form: CaseEditorForm
    saving?: boolean
    scripts?: ScriptBrief[]
    datasets?: DatasetBrief[]
    schemas?: Schemas['SchemaBrief'][]
    allowContract?: boolean
    /** 列表序号，仅展示在标题输入框前缀，不参与保存 */
    listIndex?: number
  }>(),
  {
    saving: false,
    scripts: () => [],
    datasets: () => [],
    schemas: () => [],
    allowContract: false,
    listIndex: undefined,
  },
)
defineEmits<{ save: [] }>()

const pid = useRouteParamId()
const activeTab = ref('request')
// 数据库操作处理器需按当前环境选连接（环境级）
const { databases } = useEnvDatabases()
// 数据库脚本处理器引用项目级 SQL 脚本库
const { sqlScripts } = useSqlScripts()
// 数据驱动 tab 与请求 tab 是兄弟节点：在 CaseEditor 提供，单元格 VarInput 才能看到用例变量
provideEditorVariables(() => ({
  postProcessors: props.form.post_processors ?? [],
  variableRows: props.form.variables,
}))
// 处理器由父组件加载用例后派生（deriveProcessors），本组件仅编辑 form.pre_processors/post_processors
</script>

<style scoped>
.case-list-index {
  min-width: 1.25rem;
  padding-right: 2px;
  font-size: var(--ax-font-sm);
  font-variant-numeric: tabular-nums;
  color: var(--ax-text-placeholder);
  text-align: center;
}
</style>

<template>
  <div class="case-editor">
    <div class="row1">
      <el-input v-model="form.name" placeholder="用例名称" />
      <el-button type="primary" :loading="saving" @click="$emit('save')">保存</el-button>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="请求" name="request">
        <ApiEndpointEditor :form="form" :show-meta="false" />
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
        <DataDriveEditor :model="form.data_drive" :var-rows="form.variables" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ApiEndpointEditor from '@/components/apifox/ApiEndpointEditor.vue'
import KvRowsEditor from '@/components/apifox/KvRowsEditor.vue'
import AssertionsEditor from '@/components/apifox/AssertionsEditor.vue'
import ExtractsEditor from '@/components/apifox/ExtractsEditor.vue'
import DataDriveEditor from '@/components/apifox/DataDriveEditor.vue'
import ScriptRefsEditor from '@/components/apifox/ScriptRefsEditor.vue'

defineProps({
  form: { type: Object, required: true },
  saving: { type: Boolean, default: false },
  scripts: { type: Array, default: () => [] },
})
defineEmits(['save'])

const activeTab = ref('request')
</script>

<style scoped>
.row1 {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
</style>

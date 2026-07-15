<template>
  <div class="cases-shell">
    <el-tabs v-model="tab" class="mode-tabs">
      <el-tab-pane label="测试用例" name="cases" />
      <el-tab-pane label="测试报告" name="reports" />
      <el-tab-pane label="文档" name="doc" />
    </el-tabs>

    <!-- 用例 tab 用 v-show 常驻：切去看报告/文档再切回，编辑态不丢；报告/文档 v-if 懒挂载省请求 -->
    <EndpointCasesTab v-show="tab === 'cases'" :endpoint-id="endpointId" :project-id="projectId" />
    <EndpointReportsTab v-if="tab === 'reports'" :endpoint-id="endpointId" :project-id="projectId" />
    <EndpointDocTab v-else-if="tab === 'doc'" :endpoint-id="endpointId" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import EndpointCasesTab from '@/components/apifox/EndpointCasesTab.vue'
import EndpointReportsTab from '@/components/apifox/EndpointReportsTab.vue'
import EndpointDocTab from '@/components/apifox/EndpointDocTab.vue'

defineProps({
  endpointId: { type: [String, Number], required: true },
  projectId: { type: [String, Number], required: true },
})

const tab = ref('cases')
</script>

<style scoped>
.cases-shell {
  flex: 1;
  overflow: hidden;
}

.mode-tabs {
  margin-bottom: 4px;
}
</style>

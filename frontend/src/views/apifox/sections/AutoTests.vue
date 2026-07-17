<template>
  <div class="auto-tests-root">
    <el-radio-group
      :model-value="section"
      size="small"
      class="section-switch"
      @change="switchSection"
    >
      <el-radio-button value="cases">单接口用例</el-radio-button>
      <el-radio-button value="scenarios">场景用例</el-radio-button>
      <el-radio-button value="suites">测试套件</el-radio-button>
      <el-radio-button value="datasets">数据集</el-radio-button>
      <el-radio-button value="schedules">定时任务</el-radio-button>
    </el-radio-group>

    <ScenarioPanel v-if="section === 'scenarios'" class="auto-tests" />
    <SuitePanel v-else-if="section === 'suites'" class="auto-tests" />
    <DatasetPanel v-else-if="section === 'datasets'" class="auto-tests" />
    <SchedulePanel v-else-if="section === 'schedules'" />
    <div v-else class="auto-tests">
      <ApiTreePanel :project-id="pid" @select="onSelectEndpoint" @deleted="onDeleted" />
      <ApiCasesPanel
        v-if="selectedEndpointId"
        :endpoint-id="selectedEndpointId"
        :project-id="pid"
        class="cases-area"
      />
      <el-empty v-else description="选择左侧接口，管理其测试用例" class="cases-area" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import ApiTreePanel from '@/components/apifox/ApiTreePanel.vue'
import ApiCasesPanel from '@/components/apifox/ApiCasesPanel.vue'
import ScenarioPanel from '@/views/apifox/sections/ScenarioPanel.vue'
import SuitePanel from '@/views/apifox/sections/SuitePanel.vue'
import DatasetPanel from '@/views/apifox/sections/DatasetPanel.vue'
import SchedulePanel from '@/views/apifox/sections/SchedulePanel.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const section = ref('cases')
const selectedEndpointId = ref(null)

// 场景/套件已改为多 tab：未保存态存各自 Pinia store，切子页不丢；关 tab/关浏览器时各面板兜底提示
function switchSection(next) {
  if (next !== section.value) section.value = next
}

function onSelectEndpoint(id) {
  selectedEndpointId.value = id
}

function onDeleted(id) {
  if (selectedEndpointId.value === id) selectedEndpointId.value = null
}
</script>

<style scoped>
.auto-tests-root {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.section-switch {
  margin-bottom: var(--ax-gap-sm);
  flex: none;
}

.auto-tests {
  display: flex;
  gap: var(--ax-gap-lg);
  flex: 1;
  min-height: 0;
}

.cases-area {
  flex: 1;
  overflow: auto;
  min-width: 0;
}
</style>

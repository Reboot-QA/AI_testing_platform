<template>
  <div>
    <el-radio-group v-model="section" size="small" class="section-switch">
      <el-radio-button value="cases">单接口用例</el-radio-button>
      <el-radio-button value="scenarios">场景用例</el-radio-button>
      <el-radio-button value="schedules">定时任务</el-radio-button>
    </el-radio-group>

    <ScenarioPanel v-if="section === 'scenarios'" class="auto-tests" />
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
import SchedulePanel from '@/views/apifox/sections/SchedulePanel.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const section = ref('cases')
const selectedEndpointId = ref(null)

function onSelectEndpoint(id) {
  selectedEndpointId.value = id
}

function onDeleted(id) {
  if (selectedEndpointId.value === id) selectedEndpointId.value = null
}
</script>

<style scoped>
.section-switch {
  margin-bottom: 12px;
}

.auto-tests {
  display: flex;
  gap: 16px;
  height: calc(100vh - 260px);
}

.cases-area {
  flex: 1;
  overflow: auto;
}
</style>

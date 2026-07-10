<template>
  <div class="scenario-panel">
    <div class="list-panel">
      <div class="list-toolbar">
        <span>场景</span>
        <el-button size="small" type="primary" @click="addScenario">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div
        v-for="s in scenarios"
        :key="s.id"
        class="item"
        :class="{ active: form.id === s.id }"
        @click="selectScenario(s.id)"
      >
        <el-icon><Share /></el-icon>
        <span class="item-name">{{ s.name }}</span>
        <el-tag size="small" type="info">{{ s.step_count }} 步</el-tag>
        <el-button link type="danger" size="small" @click.stop="delScenario(s)">删</el-button>
      </div>
      <el-empty v-if="scenarios.length === 0" description="暂无场景" :image-size="60" />
    </div>

    <div class="editor-panel">
      <template v-if="form.id">
        <div class="row1">
          <el-input v-model="form.name" placeholder="场景名称" style="width: 260px" />
          <el-button type="primary" :loading="saving" @click="saveScenario">保存</el-button>
          <el-button type="success" :loading="running" @click="runScenario">运行</el-button>
          <span class="run-hint">环境在顶部选择</span>
        </div>
        <el-input v-model="form.description" placeholder="描述（选填）" class="desc-input" />
        <div class="steps-title">步骤（按序执行 · 执行引擎 P4 接入）</div>
        <ScenarioStepsEditor
          :rows="form.steps"
          :cases="projectCases"
          :scenarios="scenarios"
          :current-scenario-id="form.id"
          :scripts="scripts"
        />
        <RunProgress :events="runEvents" :running="running" @clear="runEvents = []" />
      </template>
      <el-empty v-else description="选择或新建一个场景（串联接口用例形成业务链路）" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import ScenarioStepsEditor from '@/components/apifox/ScenarioStepsEditor.vue'
import RunProgress from '@/components/apifox/RunProgress.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)
const store = useWorkspaceStore()

const scenarios = ref([])
const projectCases = ref([])
const scripts = ref([])
const saving = ref(false)
const running = ref(false)
const runEvents = ref([])
const form = reactive({ id: null, name: '', description: '', steps: [] })

async function loadScenarios() {
  scenarios.value = await apifoxApi.listScenarios(pid.value)
}

async function loadProjectCases() {
  projectCases.value = await apifoxApi.listProjectCases(pid.value)
}

async function loadScripts() {
  scripts.value = await apifoxApi.listScripts(pid.value)
}

async function runScenario() {
  runEvents.value = []
  running.value = true
  try {
    await apifoxApi.runScenarioStream(form.id, store.currentEnvironmentId, (e) => runEvents.value.push(e))
  } catch (e) {
    ElMessage.error(e.message || '运行失败')
  } finally {
    running.value = false
  }
}

async function selectScenario(sid) {
  const s = await apifoxApi.getScenario(sid)
  form.id = s.id
  form.name = s.name
  form.description = s.description || ''
  form.steps = s.steps || []
}

async function addScenario() {
  const { value } = await ElMessageBox.prompt('场景名称', '新建场景', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  const created = await apifoxApi.createScenario(pid.value, { name: value, steps: [] })
  ElMessage.success('已创建')
  await loadScenarios()
  await selectScenario(created.id)
}

async function saveScenario() {
  saving.value = true
  try {
    await apifoxApi.updateScenario(form.id, {
      name: form.name,
      description: form.description || null,
      steps: form.steps.map((s) => ({
        type: s.type,
        ref_case_id: s.ref_case_id ?? null,
        ref_scenario_id: s.ref_scenario_id ?? null,
        wait_ms: s.wait_ms ?? null,
        name: s.name ?? null,
        enabled: s.enabled !== false,
      })),
    })
    ElMessage.success('已保存')
    await loadScenarios()
  } finally {
    saving.value = false
  }
}

async function delScenario(s) {
  await ElMessageBox.confirm(`确认删除场景「${s.name}」？被其他场景引用时会被拦截。`, '提示', {
    type: 'warning',
  })
  await apifoxApi.deleteScenario(s.id)
  if (form.id === s.id) form.id = null
  ElMessage.success('已删除')
  await loadScenarios()
}

onMounted(async () => {
  await loadScenarios()
  await loadProjectCases()
  await loadScripts()
})
</script>

<style scoped>
.scenario-panel {
  display: flex;
  gap: 16px;
  height: 100%;
}

.list-panel {
  width: 260px;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: 8px;
}

.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 8px;
}

.item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.item:hover {
  background: var(--ax-bg-hover);
}

.item.active {
  background: var(--ax-bg-active);
}

.item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-panel {
  flex: 1;
  overflow: auto;
}

.row1 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.run-hint {
  color: var(--ax-text-placeholder);
  font-size: 12px;
}

.desc-input {
  margin-bottom: 12px;
}

.steps-title {
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 10px;
}
</style>

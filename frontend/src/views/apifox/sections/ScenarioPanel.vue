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
        <div class="steps-title">步骤（按序执行 · 可用「分组」嵌套组织，拖拽移动）</div>
        <ScenarioStepsEditor
          :rows="form.steps"
          :cases="projectCases"
          :scenarios="scenarios"
          :current-scenario-id="form.id"
          :scripts="scripts"
          :databases="databases"
        />
        <RunProgress :events="runEvents" :running="running" @clear="runEvents = []" />
      </template>
      <el-empty v-else description="选择或新建一个场景（串联接口用例形成业务链路）" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useWorkspaceStore } from '@/stores/workspace'
import ScenarioStepsEditor from '@/components/apifox/ScenarioStepsEditor.vue'
import RunProgress from '@/components/apifox/RunProgress.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)
const store = useWorkspaceStore()

const scenarios = ref([])
const projectCases = ref([])
const scripts = ref([])
const databases = ref([])
const saving = ref(false)
const running = ref(false)
const runEvents = ref([])
const form = reactive({ id: null, name: '', description: '', steps: [], version: 1 })

async function loadScenarios() {
  scenarios.value = await apifoxApi.listScenarios(pid.value)
}

async function loadProjectCases() {
  projectCases.value = await apifoxApi.listProjectCases(pid.value)
}

async function loadScripts() {
  scripts.value = await apifoxApi.listScripts(pid.value)
}

async function loadDatabases() {
  databases.value = store.currentEnvironmentId
    ? await apifoxApi.listDatabases(store.currentEnvironmentId)
    : []
}
// 数据库连接按环境划分：切环境时重载
watch(() => store.currentEnvironmentId, loadDatabases)

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

// 后端契约树 → 前端工作态：条件(if)的 else 子步骤拆成 elseEnabled/elseChildren（便于两个独立拖放区）
function normalizeSteps(steps) {
  return (steps || []).map(normalizeStep)
}
function normalizeStep(s) {
  const node = { ...s }
  if (s.type === 'if') {
    const kids = normalizeSteps(s.children)
    const elseStep = kids.find((k) => k.type === 'else')
    node.children = kids.filter((k) => k.type !== 'else')
    node.elseEnabled = !!elseStep
    node.elseChildren = elseStep ? elseStep.children || [] : []
    if (!node.config?.condition) node.config = { condition: { left: '', operator: 'eq', right: '' } }
  } else {
    node.children = normalizeSteps(s.children)
  }
  return node
}

async function selectScenario(sid) {
  const s = await apifoxApi.getScenario(sid)
  form.id = s.id
  form.name = s.name
  form.description = s.description || ''
  form.steps = normalizeSteps(s.steps || [])
  form.version = s.version ?? 1
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

const MAX_STEP_DEPTH = 50

function leafStep(overrides) {
  return {
    type: overrides.type,
    ref_case_id: overrides.ref_case_id ?? null,
    ref_scenario_id: overrides.ref_scenario_id ?? null,
    wait_ms: overrides.wait_ms ?? null,
    config: overrides.config ?? null,
    name: overrides.name ?? null,
    enabled: overrides.enabled !== false,
    children: overrides.children || [],
  }
}

function serializeStep(s, depth = 0) {
  const deep = depth < MAX_STEP_DEPTH
  // 条件(if)：then=children，elseEnabled 时把 elseChildren 包成一个 else 子步骤（还原后端嵌套树）
  if (s.type === 'if') {
    const children = deep ? (s.children || []).map((c) => serializeStep(c, depth + 1)) : []
    if (s.elseEnabled) {
      const elseChildren = deep ? (s.elseChildren || []).map((c) => serializeStep(c, depth + 1)) : []
      children.push(leafStep({ type: 'else', children: elseChildren }))
    }
    return leafStep({ type: 'if', config: s.config, name: s.name, enabled: s.enabled, children })
  }
  const hasBody = s.type === 'group' || s.type === 'loop'
  const children = hasBody && deep ? (s.children || []).map((c) => serializeStep(c, depth + 1)) : []
  return leafStep({ ...s, children })
}

async function doSaveScenario() {
  const updated = await apifoxApi.updateScenario(form.id, {
    name: form.name,
    description: form.description || null,
    steps: form.steps.map(serializeStep),
    expected_version: form.version,
  })
  form.version = updated.version
  await loadScenarios()
}

async function saveScenario() {
  saving.value = true
  try {
    await doSaveScenario()
    ElMessage.success('已保存')
  } catch (e) {
    if (!isConflict(e)) throw e
    await resolveSaveConflict({
      reload: () => selectScenario(form.id),
      overwrite: async () => {
        const latest = await apifoxApi.getScenario(form.id)
        form.version = latest.version
        await doSaveScenario()
      },
    })
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
  await loadDatabases()
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

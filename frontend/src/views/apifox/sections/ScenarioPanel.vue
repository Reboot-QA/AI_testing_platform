<template>
  <div class="scenario-panel">
    <div class="list-panel">
      <div class="list-toolbar">
        <span>场景</span>
        <div class="toolbar-actions">
          <el-select v-model="priorityFilter" size="small" placeholder="优先级" clearable style="width: 92px">
            <el-option v-for="p in PRIORITY_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
          <el-button size="small" type="primary" @click="addScenario">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
      </div>
      <div
        v-for="s in visibleScenarios"
        :key="s.id"
        class="item"
        :class="{ active: form.id === s.id }"
        @click="onSelectScenario(s.id)"
      >
        <el-icon><Share /></el-icon>
        <span class="item-name">{{ s.name }}</span>
        <el-tag size="small" :type="priorityMeta(s.priority).type">{{ priorityMeta(s.priority).label }}</el-tag>
        <el-tag size="small" type="info">{{ s.step_count }} 步</el-tag>
        <el-button link type="danger" size="small" @click.stop="delScenario(s)">删</el-button>
      </div>
      <el-empty v-if="visibleScenarios.length === 0" description="暂无场景" :image-size="60" />
    </div>

    <div class="editor-panel">
      <template v-if="form.id">
        <div class="row1">
          <el-input v-model="form.name" placeholder="场景名称" style="width: 220px" />
          <el-select v-model="form.priority" style="width: 96px">
            <el-option v-for="p in PRIORITY_OPTIONS" :key="p.value" :label="`优先级 ${p.label}`" :value="p.value" />
          </el-select>
          <el-button type="primary" :loading="saving" @click="saveScenario">保存</el-button>
          <el-button type="success" :loading="running" @click="runScenario">运行</el-button>
          <span class="run-hint">环境在顶部选择</span>
        </div>
        <el-input v-model="form.description" placeholder="描述（选填）" class="desc-input" />
        <ScenarioRunConfigBar
          :datasets="datasets"
          v-model:loop-count="form.run_config.loop_count"
          v-model:dataset-id="form.run_config.dataset_id"
        />
        <div class="steps-title">步骤（按序执行 · 可用「分组」嵌套组织，拖拽移动）</div>
        <ScenarioStepsEditor
          :rows="form.steps"
          :cases="projectCases"
          :scenarios="scenarios"
          :current-scenario-id="form.id"
          :scripts="scripts"
          :databases="databases"
          :endpoints="endpoints"
          :server-names="serverNames"
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
import { normalizeSpec } from '@/utils/apifoxSpec'
import { isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useUnsavedGuard } from '@/composables/useUnsavedGuard'
import { useWorkspaceStore } from '@/stores/workspace'
import { PRIORITY_OPTIONS, priorityMeta, useScenarioPriorityFilter } from '@/composables/useScenarioPriority'
import ScenarioRunConfigBar from '@/components/apifox/ScenarioRunConfigBar.vue'
import ScenarioStepsEditor from '@/components/apifox/ScenarioStepsEditor.vue'
import RunProgress from '@/components/apifox/RunProgress.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)
const store = useWorkspaceStore()

const scenarios = ref([])
const projectCases = ref([])
const scripts = ref([])
const databases = ref([])
const datasets = ref([])
const endpoints = ref([])
const saving = ref(false)

// 场景 HTTP 步骤的服务名选择（取自工作区环境的命名前置 URL）
const serverNames = computed(() => {
  const names = new Set()
  store.environments.forEach((e) => (e.servers || []).forEach((s) => names.add(s.name)))
  return [...names]
})
const running = ref(false)
const runEvents = ref([])
const form = reactive({
  id: null, name: '', description: '', priority: 'medium', steps: [], version: 1,
  run_config: { loop_count: 1, dataset_id: null },
})
const { priorityFilter, visibleScenarios } = useScenarioPriorityFilter(scenarios)

async function loadScenarios() {
  scenarios.value = await apifoxApi.listScenarios(pid.value)
}

async function loadProjectCases() {
  projectCases.value = await apifoxApi.listProjectCases(pid.value)
}

async function loadScripts() {
  scripts.value = await apifoxApi.listScripts(pid.value)
}

async function loadDatasets() {
  datasets.value = await apifoxApi.listDatasets(pid.value)
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
  } else if (s.type === 'http') {
    // http 步骤：补全 request_spec 结构供编辑器绑定，保证 assertions/extracts 为数组
    const c = s.config || {}
    node.config = {
      ...c,
      request_spec: normalizeSpec(c.request_spec),
      assertions: c.assertions || [],
      extracts: c.extracts || [],
    }
  } else {
    node.children = normalizeSteps(s.children)
  }
  return node
}

// 未保存保护：切换场景/切主 tab/关浏览器前，dirty 则提示
const guard = useUnsavedGuard({
  serialize: () => JSON.stringify({
    name: form.name, description: form.description, priority: form.priority,
    steps: form.steps, run_config: form.run_config,
  }),
  save: () => saveScenario(),
  name: () => form.name,
})
// 暴露给父组件 AutoTests：v-if 切子页(非路由)时先过守卫，避免未保存改动被静默卸载丢弃
defineExpose({ confirmLeave: guard.confirmLeave })

async function selectScenario(sid) {
  const s = await apifoxApi.getScenario(sid)
  form.id = s.id
  form.name = s.name
  form.description = s.description || ''
  form.priority = s.priority || 'medium'
  form.steps = normalizeSteps(s.steps || [])
  form.version = s.version ?? 1
  form.run_config = {
    loop_count: s.run_config?.loop_count ?? 1,
    dataset_id: s.run_config?.dataset_id ?? null,
  }
  guard.markSaved() // 加载后重置未保存基线
}

// 列表点选（用户主动切换）：先过未保存守卫
async function onSelectScenario(id) {
  if (id === form.id) return
  if (!(await guard.confirmLeave())) return
  await selectScenario(id)
}

async function addScenario() {
  if (!(await guard.confirmLeave())) return // 当前有未保存改动时先确认
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
    priority: form.priority,
    steps: form.steps.map(serializeStep),
    run_config: {
      loop_count: form.run_config.loop_count || 1,
      dataset_id: form.run_config.dataset_id || null, // el-select 清空可能给 ''，统一收敛为 null
    },
    expected_version: form.version,
  })
  form.version = updated.version
  await loadScenarios()
}

async function saveScenario() {
  saving.value = true
  try {
    await doSaveScenario()
    guard.markSaved()
    ElMessage.success('已保存')
    return true
  } catch (e) {
    if (!isConflict(e)) return false // 非冲突错误已由 api 拦截器提示，不外抛(避免穿透 confirmLeave)
    let resolved = false
    await resolveSaveConflict({
      reload: async () => {
        await selectScenario(form.id)
        resolved = true
      },
      overwrite: async () => {
        const latest = await apifoxApi.getScenario(form.id)
        form.version = latest.version
        await doSaveScenario()
        guard.markSaved()
        resolved = true
      },
    })
    return resolved
  } finally {
    saving.value = false
  }
}

async function delScenario(s) {
  await ElMessageBox.confirm(`确认删除场景「${s.name}」？被其他场景引用时会被拦截。`, '提示', {
    type: 'warning',
  })
  await apifoxApi.deleteScenario(s.id)
  if (form.id === s.id) {
    // 删的是当前编辑项：清空表单 + 校正未保存基线，避免后续误报 dirty/对已删项发保存
    form.id = null
    form.name = ''
    form.description = ''
    form.steps = []
    form.version = 1
    form.run_config = { loop_count: 1, dataset_id: null }
    guard.markSaved()
  }
  ElMessage.success('已删除')
  await loadScenarios()
}

onMounted(async () => {
  await loadScenarios()
  await loadProjectCases()
  await loadScripts()
  await loadDatabases()
  await loadDatasets()
  endpoints.value = await apifoxApi.listEndpoints(pid.value)
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

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
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

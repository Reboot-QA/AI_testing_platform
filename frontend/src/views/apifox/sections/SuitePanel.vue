<template>
  <div class="suite-panel">
    <div class="list-panel">
      <div class="list-toolbar">
        <span>测试套件</span>
        <el-button size="small" type="primary" @click="addSuite">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div
        v-for="s in suites"
        :key="s.id"
        class="item"
        :class="{ active: form.id === s.id }"
        @click="selectSuite(s.id)"
      >
        <el-icon><Files /></el-icon>
        <span class="item-name">{{ s.name }}</span>
        <el-tag size="small" type="info">{{ s.item_count }} 项</el-tag>
        <el-button link type="danger" size="small" @click.stop="delSuite(s)">删</el-button>
      </div>
      <el-empty v-if="suites.length === 0" description="暂无套件" :image-size="60" />
    </div>

    <div class="editor-panel">
      <template v-if="form.id">
        <div class="row1">
          <el-input v-model="form.name" placeholder="套件名称" style="width: 260px" />
          <el-button type="primary" :loading="saving" @click="saveSuite">保存</el-button>
          <el-button type="success" :loading="running" @click="runSuite">运行</el-button>
          <span class="run-hint">每项独立执行 · 环境在顶部选择</span>
        </div>
        <el-input v-model="form.description" placeholder="描述（选填）" class="desc-input" />

        <div class="items-title">套件项（按序批量执行 · 拖拽调整顺序）</div>
        <VueDraggable v-model="form.items" handle=".drag-handle" :animation="150">
          <div v-for="(it, i) in form.items" :key="it._uid" class="suite-item">
            <el-icon class="drag-handle"><Rank /></el-icon>
            <el-switch v-model="it.enabled" size="small" />
            <el-tag size="small" :type="it.target_type === 'scenario' ? 'warning' : ''">
              {{ it.target_type === 'scenario' ? '场景' : '用例' }}
            </el-tag>
            <MethodTag v-if="it.endpoint_method" :method="it.endpoint_method" />
            <span class="si-name">{{ it.target_name }}</span>
            <el-button link type="danger" size="small" @click="form.items.splice(i, 1)">移除</el-button>
          </div>
        </VueDraggable>
        <el-empty v-if="form.items.length === 0" description="下方添加用例或场景" :image-size="50" />

        <div class="add-row">
          <el-select
            v-model="pickCase"
            filterable
            clearable
            placeholder="+ 添加用例"
            size="small"
            class="picker"
            @change="onPickCase"
          >
            <el-option v-for="c in projectCases" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-select
            v-model="pickScenario"
            filterable
            clearable
            placeholder="+ 添加场景"
            size="small"
            class="picker"
            @change="onPickScenario"
          >
            <el-option v-for="s in scenarios" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </div>

        <SuiteRunProgress :events="runEvents" :running="running" @clear="runEvents = []" />
      </template>
      <el-empty v-else description="选择或新建一个套件（把用例/场景成组批量回归）" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VueDraggable } from 'vue-draggable-plus'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import MethodTag from '@/components/apifox/common/MethodTag.vue'
import SuiteRunProgress from '@/components/apifox/SuiteRunProgress.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)
const store = useWorkspaceStore()

const suites = ref([])
const projectCases = ref([])
const scenarios = ref([])
const saving = ref(false)
const running = ref(false)
const runEvents = ref([])
const pickCase = ref(null)
const pickScenario = ref(null)
const form = reactive({ id: null, name: '', description: '', items: [] })

let uid = 0
const nextUid = () => `si-${uid++}`

async function loadSuites() {
  suites.value = await apifoxApi.listSuites(pid.value)
}

async function selectSuite(sid) {
  const s = await apifoxApi.getSuite(sid)
  form.id = s.id
  form.name = s.name
  form.description = s.description || ''
  form.items = (s.items || []).map((it) => ({ ...it, _uid: nextUid() }))
}

async function addSuite() {
  const { value } = await ElMessageBox.prompt('套件名称', '新建套件', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  const created = await apifoxApi.createSuite(pid.value, { name: value, items: [] })
  ElMessage.success('已创建')
  await loadSuites()
  await selectSuite(created.id)
}

function onPickCase(id) {
  if (!id) return
  const c = projectCases.value.find((x) => x.id === id)
  form.items.push({
    _uid: nextUid(),
    target_type: 'case',
    target_id: id,
    target_name: c?.name || '',
    endpoint_method: c?.endpoint_method || '',
    enabled: true,
  })
  pickCase.value = null
}

function onPickScenario(id) {
  if (!id) return
  const s = scenarios.value.find((x) => x.id === id)
  form.items.push({
    _uid: nextUid(),
    target_type: 'scenario',
    target_id: id,
    target_name: s?.name || '',
    endpoint_method: '',
    enabled: true,
  })
  pickScenario.value = null
}

async function saveSuite() {
  saving.value = true
  try {
    await apifoxApi.updateSuite(form.id, {
      name: form.name,
      description: form.description || null,
      items: form.items.map((it) => ({
        target_type: it.target_type,
        target_id: it.target_id,
        enabled: it.enabled !== false,
      })),
    })
    ElMessage.success('已保存')
    await loadSuites()
  } finally {
    saving.value = false
  }
}

async function runSuite() {
  runEvents.value = []
  running.value = true
  try {
    await apifoxApi.runSuiteStream(form.id, store.currentEnvironmentId, (e) => runEvents.value.push(e))
  } catch (e) {
    ElMessage.error(e.message || '运行失败')
  } finally {
    running.value = false
  }
}

async function delSuite(s) {
  await ElMessageBox.confirm(`确认删除套件「${s.name}」？`, '提示', { type: 'warning' })
  await apifoxApi.deleteSuite(s.id)
  if (form.id === s.id) form.id = null
  ElMessage.success('已删除')
  await loadSuites()
}

onMounted(async () => {
  await loadSuites()
  projectCases.value = await apifoxApi.listProjectCases(pid.value)
  scenarios.value = await apifoxApi.listScenarios(pid.value)
})
</script>

<style scoped>
.suite-panel {
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

.items-title {
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 10px;
}

.suite-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border: 1px solid var(--ax-border);
  border-radius: 4px;
  margin-bottom: 6px;
  background: var(--ax-bg-subtle);
}

.drag-handle {
  cursor: move;
  color: var(--ax-text-placeholder);
}

.si-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.add-row {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.picker {
  width: 200px;
}
</style>

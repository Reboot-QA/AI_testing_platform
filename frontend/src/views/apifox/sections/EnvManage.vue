<template>
  <div class="env-manage">
    <div class="list-panel">
      <div class="list-toolbar">
        <span>环境</span>
        <el-button size="small" type="primary" @click="addEnv">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div
        v-for="e in environments"
        :key="e.id"
        class="env-item"
        :class="{ active: selected.type === 'env' && selected.id === e.id }"
        @click="selectEnv(e)"
      >
        <span class="env-name">{{ e.name }}</span>
        <el-tag v-if="e.is_default" size="small" type="success">默认</el-tag>
        <span class="env-ops">
          <el-button link size="small" @click.stop="renameEnv(e)">改名</el-button>
          <el-button link size="small" @click.stop="setDefault(e)">设默认</el-button>
          <el-button link size="small" type="danger" @click.stop="delEnv(e)">删</el-button>
        </span>
      </div>

      <div
        class="env-item global"
        :class="{ active: selected.type === 'global' }"
        @click="selectGlobal"
      >
        <el-icon><Star /></el-icon>
        <span class="env-name">全局变量</span>
      </div>
    </div>

    <div class="var-panel">
      <div class="var-title">
        {{ selected.type === 'global' ? '全局变量（项目级，跨环境）' : `环境变量 · ${selectedName}` }}
      </div>
      <VariableTable
        :variables="vars"
        @create="onCreate"
        @update="onUpdate"
        @delete="onDelete"
        @set-local="onSetLocal"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import VariableTable from '@/components/apifox/VariableTable.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const environments = ref([])
const vars = ref([])
const selected = reactive({ type: 'global', id: null })

const selectedName = computed(() => environments.value.find((e) => e.id === selected.id)?.name || '')

async function loadEnvs() {
  environments.value = await apifoxApi.listEnvironments(pid.value)
}

async function reloadVars() {
  if (selected.type === 'env') vars.value = await apifoxApi.listEnvVars(selected.id)
  else vars.value = await apifoxApi.listGlobalVars(pid.value)
}

function selectEnv(e) {
  selected.type = 'env'
  selected.id = e.id
  reloadVars()
}

function selectGlobal() {
  selected.type = 'global'
  selected.id = null
  reloadVars()
}

async function addEnv() {
  const { value } = await ElMessageBox.prompt('环境名称', '新建环境', { inputPattern: /\S/, inputErrorMessage: '不能为空' })
  await apifoxApi.createEnvironment(pid.value, { name: value })
  ElMessage.success('已创建')
  await loadEnvs()
}

async function renameEnv(e) {
  const { value } = await ElMessageBox.prompt('新名称', '改名', { inputValue: e.name, inputPattern: /\S/, inputErrorMessage: '不能为空' })
  await apifoxApi.updateEnvironment(e.id, { name: value })
  await loadEnvs()
}

async function setDefault(e) {
  await apifoxApi.updateEnvironment(e.id, { is_default: true })
  await loadEnvs()
}

async function delEnv(e) {
  await ElMessageBox.confirm(`确认删除环境「${e.name}」及其变量？`, '提示', { type: 'warning' })
  await apifoxApi.deleteEnvironment(e.id)
  ElMessage.success('已删除')
  if (selected.type === 'env' && selected.id === e.id) selectGlobal()
  await loadEnvs()
}

async function onCreate(payload) {
  try {
    if (selected.type === 'env') await apifoxApi.createEnvVar(selected.id, payload)
    else await apifoxApi.createGlobalVar(pid.value, payload)
    await reloadVars()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

async function onUpdate(id, payload) {
  if (selected.type === 'env') await apifoxApi.updateEnvVar(id, payload)
  else await apifoxApi.updateGlobalVar(id, payload)
  await reloadVars()
}

async function onDelete(id) {
  if (selected.type === 'env') await apifoxApi.deleteEnvVar(id)
  else await apifoxApi.deleteGlobalVar(id)
  await reloadVars()
}

async function onSetLocal(id, value) {
  if (selected.type === 'env') await apifoxApi.setEnvVarLocal(id, value)
  else await apifoxApi.setGlobalVarLocal(id, value)
  await reloadVars()
}

onMounted(async () => {
  await loadEnvs()
  await reloadVars()
})
</script>

<style scoped>
.env-manage {
  display: flex;
  gap: 16px;
  height: calc(100vh - 220px);
}

.list-panel {
  width: 240px;
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

.env-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.env-item:hover {
  background: var(--ax-bg-hover);
}

.env-item.active {
  background: var(--ax-bg-active);
}

.env-item.global {
  margin-top: 12px;
  border-top: 1px solid var(--ax-border);
  padding-top: 12px;
}

.env-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.env-ops {
  display: none;
}

.env-item:hover .env-ops {
  display: inline-flex;
}

.var-panel {
  flex: 1;
  overflow: auto;
}

.var-title {
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 12px;
}
</style>

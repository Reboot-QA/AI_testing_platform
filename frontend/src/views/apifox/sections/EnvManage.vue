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
      <div class="env-item" :class="{ active: selected.type === 'params' }" @click="selectParams">
        <el-icon><SetUp /></el-icon>
        <span class="env-name">全局参数</span>
      </div>
    </div>

    <div class="var-panel">
      <GlobalParamsPanel v-if="selected.type === 'params'" :project-id="pid" />
      <template v-else>
        <template v-if="selected.type === 'env'">
          <div class="var-title">前置 URL · {{ selectedName }}</div>
          <div class="base-row">
            <span class="base-label">默认前置 URL</span>
            <el-input
              v-model="baseUrl"
              size="small"
              placeholder="如 https://api.xxx.com（接口相对路径会拼在它前面）"
              @change="saveBaseUrl"
            />
          </div>
          <div v-for="s in servers" :key="s.id" class="server-row">
            <el-input
              v-model="s.name"
              size="small"
              placeholder="名称(如 服务A)"
              style="width: 160px"
              @change="saveServer(s)"
            />
            <el-input v-model="s.base_url" size="small" placeholder="URL" @change="saveServer(s)" />
            <el-button link type="danger" size="small" @click="delServer(s)">删</el-button>
          </div>
          <div class="add-server">
            <el-input
              v-model="newServer.name"
              size="small"
              placeholder="名称"
              style="width: 160px"
            />
            <el-input v-model="newServer.base_url" size="small" placeholder="URL" />
            <el-button
              size="small"
              type="primary"
              :disabled="!newServer.name.trim()"
              @click="addServer"
            >
              + 命名前置 URL
            </el-button>
          </div>
        </template>

        <div class="var-title" :style="{ marginTop: selected.type === 'env' ? '18px' : '0' }">
          {{
            selected.type === 'global' ? '全局变量（项目级，跨环境）' : `环境变量 · ${selectedName}`
          }}
        </div>
        <VariableTable
          :variables="vars"
          @create="onCreate"
          @update="onUpdate"
          @delete="onDelete"
          @set-local="onSetLocal"
        />
        <EnvDatabasesPanel v-if="selected.type === 'env'" :environment-id="selected.id" />
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import VariableTable from '@/components/apifox/VariableTable.vue'
import GlobalParamsPanel from '@/components/apifox/GlobalParamsPanel.vue'
import EnvDatabasesPanel from '@/components/apifox/EnvDatabasesPanel.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)
const store = useWorkspaceStore()

const environments = ref([])
const vars = ref([])
const servers = ref([])
const baseUrl = ref('')
const newServer = reactive({ name: '', base_url: '' })
const selected = reactive({ type: 'global', id: null })

const selectedName = computed(
  () => environments.value.find((e) => e.id === selected.id)?.name || '',
)

async function loadEnvs() {
  environments.value = await apifoxApi.listEnvironments(pid.value)
  // 同步共享 store：让接口调试「前置URL」下拉、顶部环境选择器、场景编辑器拿到最新命名前置URL（保留当前选中环境）
  store.setEnvironments(environments.value)
  syncEnvDetail()
}

function syncEnvDetail() {
  const e = environments.value.find((x) => x.id === selected.id)
  if (selected.type === 'env' && e) {
    baseUrl.value = e.base_url || ''
    servers.value = (e.servers || []).map((s) => ({ ...s }))
  }
}

async function saveBaseUrl() {
  await apifoxApi.updateEnvironment(selected.id, { base_url: baseUrl.value })
  await loadEnvs()
}

async function addServer() {
  try {
    await apifoxApi.createEnvServer(selected.id, {
      name: newServer.name.trim(),
      base_url: newServer.base_url,
    })
    newServer.name = ''
    newServer.base_url = ''
    await loadEnvs()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  }
}

async function saveServer(s) {
  try {
    await apifoxApi.updateEnvServer(s.id, { name: s.name, base_url: s.base_url })
    await loadEnvs()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

async function delServer(s) {
  await apifoxApi.deleteEnvServer(s.id)
  await loadEnvs()
}

async function reloadVars() {
  if (selected.type === 'env') vars.value = await apifoxApi.listEnvVars(selected.id)
  else vars.value = await apifoxApi.listGlobalVars(pid.value)
}

function selectEnv(e) {
  selected.type = 'env'
  selected.id = e.id
  syncEnvDetail()
  reloadVars()
}

function selectGlobal() {
  selected.type = 'global'
  selected.id = null
  reloadVars()
}

function selectParams() {
  selected.type = 'params'
  selected.id = null
}

async function addEnv() {
  const { value } = await ElMessageBox.prompt('环境名称', '新建环境', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  await apifoxApi.createEnvironment(pid.value, { name: value })
  ElMessage.success('已创建')
  await loadEnvs()
}

async function renameEnv(e) {
  const { value } = await ElMessageBox.prompt('新名称', '改名', {
    inputValue: e.name,
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
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

.base-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.base-label {
  flex-shrink: 0;
  font-size: 13px;
  color: var(--ax-text-secondary);
}

.server-row,
.add-server {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
</style>

<template>
  <div class="env-manage">
    <div class="env-manage-body">
      <div class="list-panel">
        <div class="panel-head">
          <span class="panel-title">环境</span>
          <el-button type="primary" size="small" title="新建环境" @click="addEnv">
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
          <el-dropdown trigger="click" @command="(cmd: EnvOpCommand) => onEnvCommand(cmd, e)">
            <el-button text size="small" class="env-more-btn" title="更多操作" @click.stop>
              <el-icon><MoreFilled /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="rename">改名</el-dropdown-item>
                <el-dropdown-item command="default" :disabled="e.is_default">
                  设为默认
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <span class="env-delete-label">删除</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
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
        <div class="env-item" :class="{ active: selected.type === 'limits' }" @click="selectLimits">
          <el-icon><InfoFilled /></el-icon>
          <span class="env-name">输入限制</span>
        </div>
      </div>

      <div class="var-panel">
        <EnvLimitsHelpPanel v-if="selected.type === 'limits'" />
        <GlobalParamsPanel v-else-if="selected.type === 'params'" :project-id="pid" />
        <template v-else>
          <template v-if="selected.type === 'env'">
            <section class="env-section">
              <div class="var-title">前置 URL · {{ selectedName }}</div>
              <div class="base-row">
                <span class="base-label">默认前置 URL</span>
                <el-input
                  v-model="baseUrl"
                  size="small"
                  :maxlength="URL_MAX_LEN"
                  placeholder="如 https://api.xxx.com（接口相对路径会拼在它前面）"
                />
              </div>
            </section>

            <section class="env-section">
              <div class="var-title">命名服务</div>
              <div v-for="s in servers" :key="s.id" class="server-row">
                <el-input
                  v-model="s.name"
                  size="small"
                  :maxlength="TITLE_MAX_LEN"
                  placeholder="名称(如 服务A)"
                  class="server-name"
                />
                <el-input
                  v-model="s.base_url"
                  size="small"
                  :maxlength="URL_MAX_LEN"
                  placeholder="URL"
                />
                <el-button link type="danger" size="small" @click="delServer(s)">删</el-button>
              </div>
              <div class="server-row">
                <el-input
                  v-model="draftServer.name"
                  size="small"
                  :maxlength="TITLE_MAX_LEN"
                  placeholder="名称"
                  class="server-name"
                  @keyup.enter="commitDraftServer"
                />
                <el-input
                  v-model="draftServer.base_url"
                  size="small"
                  :maxlength="URL_MAX_LEN"
                  placeholder="URL"
                  @blur="commitDraftServer"
                  @keyup.enter="commitDraftServer"
                />
              </div>
            </section>

            <section class="env-section">
              <el-popover
                placement="top"
                trigger="hover"
                :width="'auto'"
                :show-after="300"
                popper-class="var-value-popover"
              >
                <template #reference>
                  <div class="var-title var-title--clamp">环境变量 · {{ selectedName }}</div>
                </template>
                <div class="var-value-popover__body">环境变量 · {{ selectedName }}</div>
              </el-popover>
              <VariableTable
                :variables="vars"
                @create="onCreate"
                @update="onUpdate"
                @delete="onDelete"
                @set-local="onSetLocal"
              />
            </section>

            <section v-if="selected.id != null" class="env-section">
              <EnvDatabasesPanel :environment-id="selected.id" />
            </section>
          </template>

          <template v-else>
            <section class="env-section">
              <el-popover
                placement="top"
                trigger="hover"
                :width="'auto'"
                :show-after="300"
                popper-class="var-value-popover"
              >
                <template #reference>
                  <div class="var-title var-title--clamp">全局变量</div>
                </template>
                <div class="var-value-popover__body">全局变量（项目级，跨环境）</div>
              </el-popover>
              <VariableTable
                :variables="vars"
                @create="onCreate"
                @update="onUpdate"
                @delete="onDelete"
                @set-local="onSetLocal"
              />
            </section>
          </template>
        </template>
      </div>
    </div>

    <div class="env-manage-footer">
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      <el-button
        v-if="showCloseAction"
        type="primary"
        :loading="saving"
        @click="handleSaveAndClose"
      >
        保存并关闭
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouteParamId } from '@/composables/useRouteParamId'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { TITLE_MAX_LEN, URL_MAX_LEN } from '@/constants/limits'
import { nameInputOptions } from '@/utils/promptLimits'
import { useWorkspaceStore } from '@/stores/workspace'
import { useResolvableVarsReload } from '@/composables/useResolvableVars'
import VariableTable from '@/components/apifox/project/VariableTable.vue'
import GlobalParamsPanel from '@/components/apifox/project/GlobalParamsPanel.vue'
import EnvDatabasesPanel from '@/components/apifox/project/EnvDatabasesPanel.vue'
import EnvLimitsHelpPanel from '@/components/apifox/project/EnvLimitsHelpPanel.vue'

const props = withDefaults(
  defineProps<{
    showCloseAction?: boolean
    initialEnvId?: number | null
  }>(),
  {
    showCloseAction: false,
    initialEnvId: null,
  },
)

const emit = defineEmits<{
  saved: []
  close: []
}>()

const pid = useRouteParamId()
const store = useWorkspaceStore()
const reloadResolvableVars = useResolvableVarsReload()

type EnvOpCommand = 'rename' | 'default' | 'delete'

const saving = ref(false)
const didInitialSelect = ref(false)

const environments = ref<Schemas['EnvironmentOut'][]>([])
const vars = ref<Schemas['VariableOut'][]>([])
const servers = ref<Schemas['ServerOut'][]>([])
const baseUrl = ref('')
const draftServer = reactive({ name: '', base_url: '' })
const committingDraft = ref(false)
const selected = reactive<{
  type: 'global' | 'env' | 'params' | 'limits'
  id: number | null
}>({
  type: 'global',
  id: null,
})

const selectedName = computed(
  () => environments.value.find((e) => e.id === selected.id)?.name || '',
)

async function loadEnvs() {
  environments.value = await apifoxApi.listEnvironments(pid.value)
  // 同步共享 store：让接口调试「前置URL」下拉、顶部环境选择器、场景编辑器拿到最新命名前置URL（保留当前选中环境）
  store.setEnvironments(environments.value)
  syncEnvDetail()
}

function applyInitialSelection() {
  if (didInitialSelect.value) return
  didInitialSelect.value = true
  const list = environments.value
  if (list.length === 0) {
    selected.type = 'global'
    selected.id = null
    return
  }
  const byId =
    props.initialEnvId != null ? list.find((e) => e.id === props.initialEnvId) : undefined
  const byDefault = list.find((e) => e.is_default)
  const target = byId ?? byDefault ?? list[0]
  selected.type = 'env'
  selected.id = target.id
  syncEnvDetail()
}

function syncEnvDetail() {
  const e = environments.value.find((x) => x.id === selected.id)
  if (selected.type === 'env' && e) {
    baseUrl.value = e.base_url || ''
    servers.value = (e.servers || []).map((s) => ({ ...s }))
    draftServer.name = ''
    draftServer.base_url = ''
  }
}

async function persistEnvConfig(): Promise<void> {
  if (selected.type !== 'env' || selected.id == null) return
  await apifoxApi.updateEnvironment(selected.id, { base_url: baseUrl.value })
  await Promise.all(
    servers.value.map((s) =>
      apifoxApi.updateEnvServer(s.id, { name: s.name, base_url: s.base_url }),
    ),
  )
}

async function persistChanges(): Promise<void> {
  await persistEnvConfig()
  await loadEnvs()
}

async function handleSave(): Promise<void> {
  saving.value = true
  try {
    await persistChanges()
    ElMessage.success('已保存')
    emit('saved')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function handleSaveAndClose(): Promise<void> {
  saving.value = true
  try {
    await persistChanges()
    ElMessage.success('已保存')
    emit('saved')
    emit('close')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function commitDraftServer() {
  const name = draftServer.name.trim()
  if (selected.id == null || !name || committingDraft.value) return
  committingDraft.value = true
  try {
    await apifoxApi.createEnvServer(selected.id, {
      name,
      base_url: draftServer.base_url.trim(),
    })
    draftServer.name = ''
    draftServer.base_url = ''
    await loadEnvs()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err.response?.data?.detail || '添加失败')
  } finally {
    committingDraft.value = false
  }
}

async function delServer(s: Schemas['ServerOut']) {
  await apifoxApi.deleteEnvServer(s.id)
  await loadEnvs()
}

async function reloadVars() {
  if (selected.type === 'env' && selected.id != null)
    vars.value = await apifoxApi.listEnvVars(selected.id)
  else vars.value = await apifoxApi.listGlobalVars(pid.value)
}

function selectEnv(e: Schemas['EnvironmentOut']) {
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

function selectLimits() {
  selected.type = 'limits'
  selected.id = null
}

function onEnvCommand(cmd: EnvOpCommand, e: Schemas['EnvironmentOut']) {
  if (cmd === 'rename') renameEnv(e)
  else if (cmd === 'default') setDefault(e)
  else if (cmd === 'delete') delEnv(e)
}

async function addEnv() {
  const { value } = await ElMessageBox.prompt('环境名称', '新建环境', {
    ...nameInputOptions(),
  })
  await apifoxApi.createEnvironment(pid.value, { name: value, is_default: false })
  ElMessage.success('已创建')
  await loadEnvs()
}

async function renameEnv(e: Schemas['EnvironmentOut']) {
  const { value } = await ElMessageBox.prompt('新名称', '改名', {
    inputValue: e.name,
    ...nameInputOptions(),
  })
  await apifoxApi.updateEnvironment(e.id, { name: value })
  await loadEnvs()
}

async function setDefault(e: Schemas['EnvironmentOut']) {
  await apifoxApi.updateEnvironment(e.id, { is_default: true })
  await loadEnvs()
}

async function delEnv(e: Schemas['EnvironmentOut']) {
  await ElMessageBox.confirm(`确认删除环境「${e.name}」及其变量？`, '提示', { type: 'warning' })
  await apifoxApi.deleteEnvironment(e.id)
  ElMessage.success('已删除')
  if (selected.type === 'env' && selected.id === e.id) selectGlobal()
  await loadEnvs()
}

async function onCreate(payload: Schemas['VariableCreate']) {
  try {
    if (selected.type === 'env' && selected.id != null)
      await apifoxApi.createEnvVar(selected.id, payload)
    else await apifoxApi.createGlobalVar(pid.value, payload)
    await reloadVars()
    await reloadResolvableVars()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    ElMessage.error(err.response?.data?.detail || '创建失败')
  }
}

async function onUpdate(id: number, payload: Partial<Schemas['VariableOut']>) {
  if (selected.type === 'env') await apifoxApi.updateEnvVar(id, payload)
  else await apifoxApi.updateGlobalVar(id, payload)
  await reloadVars()
  await reloadResolvableVars()
}

async function onDelete(id: number) {
  if (selected.type === 'env') await apifoxApi.deleteEnvVar(id)
  else await apifoxApi.deleteGlobalVar(id)
  await reloadVars()
  await reloadResolvableVars()
}

async function onSetLocal(id: number, value: string | null) {
  if (selected.type === 'env') await apifoxApi.setEnvVarLocal(id, value)
  else await apifoxApi.setGlobalVarLocal(id, value)
  await reloadVars()
  await reloadResolvableVars()
}

onMounted(async () => {
  await loadEnvs()
  applyInitialSelection()
  await reloadVars()
})
</script>

<style scoped>
.env-manage {
  display: flex;
  flex-direction: column;
  gap: 0;
  height: 100%;
  min-height: 0;
}

.env-manage-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: var(--ax-gap-lg);
  overflow: hidden;
}

.env-manage-footer {
  flex: none;
  display: flex;
  justify-content: flex-end;
  gap: var(--ax-space-2);
  padding-top: var(--ax-space-3);
  margin-top: var(--ax-space-2);
  border-top: 1px solid var(--ax-border);
}

/* list-panel / panel-head / panel-title 见 apifox-workspace.css */
.list-panel {
  /* 抽屉内让出更多宽度给变量宽表，减少横滑 */
  width: 220px;
}

.env-item {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  padding: var(--ax-space-1-5) var(--ax-space-2);
  border-radius: var(--ax-radius-sm);
  cursor: pointer;
}

.env-item:hover {
  background: var(--ax-bg-hover);
}

.env-item.active {
  background: var(--ax-bg-active);
}

.env-item.global {
  margin-top: var(--ax-space-3);
  border-top: 1px solid var(--ax-border);
  padding-top: var(--ax-space-3);
}

.env-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-font-sm);
}

.env-more-btn {
  flex: none;
  opacity: 0;
  padding: var(--ax-space-0) var(--ax-space-1);
}

.env-item:hover .env-more-btn,
.env-item.active .env-more-btn {
  opacity: 1;
}

.env-delete-label {
  color: var(--ax-danger);
}

.var-panel {
  flex: 1;
  min-width: 0;
  /* 纵向滚动在面板；横向交给表格内部可见滚动条，避免双层横滚卡顿 */
  overflow-x: hidden;
  overflow-y: auto;
}

.env-section {
  margin-bottom: var(--ax-drawer-section-gap);
}

.env-section:last-child {
  margin-bottom: 0;
}

.env-section :deep(.db-panel) {
  margin-top: 0;
}

.var-title {
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: var(--ax-space-3);
}

/* 覆盖 workspace 的 nowrap：最多 3 行，超出省略；完整文案见 popover */
.var-title--clamp {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
  white-space: normal;
  word-break: break-word;
  max-width: 100%;
}

.base-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.base-label {
  flex-shrink: 0;
  font-size: var(--ax-font-sm);
  color: var(--ax-text-secondary);
}

.server-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
}

.server-row:last-child {
  margin-bottom: 0;
}

.server-name {
  width: 160px;
  flex: none;
}
</style>

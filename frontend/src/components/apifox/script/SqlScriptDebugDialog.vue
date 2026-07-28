<template>
  <el-dialog
    :model-value="visible"
    title="调试 SQL 脚本"
    width="720px"
    @update:model-value="emit('update:visible', $event)"
    @open="onOpen"
  >
    <div class="sd">
      <div class="sd-row">
        <span class="sd-lbl">环境</span>
        <el-select v-model="envId" size="small" placeholder="选择环境" style="width: 200px">
          <el-option v-for="e in environments" :key="e.id" :label="e.name" :value="e.id" />
        </el-select>
        <span class="sd-lbl">连接</span>
        <el-select v-model="connectionId" size="small" placeholder="选择数据库连接" style="flex: 1">
          <el-option
            v-for="d in databases"
            :key="d.id"
            :label="`${d.name}（${d.host}/${d.database}）`"
            :value="d.id"
          />
        </el-select>
        <el-button link type="primary" size="small" @click="openManage">管理连接</el-button>
      </div>
      <p class="sd-tip">
        调试会用该连接真实执行 SQL（含写操作），执行前会二次确认。结果仅预览，不写变量。
      </p>

      <div v-if="result" class="sd-result">
        <div class="sd-status">
          <el-tag :type="result.status === 'passed' ? 'success' : 'danger'" size="small">
            {{ result.status === 'passed' ? '成功' : '失败' }}
          </el-tag>
          <span class="sd-count">影响/结果行数：{{ result.row_count }}</span>
        </div>
        <p v-if="result.error_message" class="sd-error">{{ result.error_message }}</p>
        <el-table
          v-if="result.preview_rows?.length"
          :data="result.preview_rows"
          size="small"
          border
          max-height="280"
        >
          <el-table-column
            v-for="col in previewColumns"
            :key="col"
            :prop="col"
            :label="col"
            min-width="100"
          />
        </el-table>
      </div>
    </div>

    <template #footer>
      <el-button @click="emit('update:visible', false)">关闭</el-button>
      <el-button type="primary" :loading="running" :disabled="!connectionId" @click="run">
        执行
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { useDatabaseManageDrawer } from '@/composables/useDatabaseManageDrawer'

const props = defineProps<{ visible: boolean; content: string }>()
const emit = defineEmits<{ 'update:visible': [v: boolean] }>()

const workspace = useWorkspaceStore()
const environments = computed(() => workspace.environments)
const envId = ref<number | null>(workspace.currentEnvironmentId)
const databases = ref<Schemas['DatabaseOut'][]>([])
const connectionId = ref<number | null>(null)
const running = ref(false)
const result = ref<Schemas['SqlScriptDebugOut'] | null>(null)

const previewColumns = computed(() =>
  result.value?.preview_rows?.length ? Object.keys(result.value.preview_rows[0]) : [],
)

async function loadDatabases() {
  databases.value = envId.value ? await apifoxApi.listDatabases(envId.value) : []
  if (!databases.value.some((d) => d.id === connectionId.value)) connectionId.value = null
}

watch(envId, loadDatabases)

const { open: openDatabaseManage, subscribeUpdated } = useDatabaseManageDrawer()

onMounted(() => {
  const unsub = subscribeUpdated(loadDatabases)
  onUnmounted(unsub)
})

function openManage() {
  openDatabaseManage(envId.value, { create: databases.value.length === 0 })
}

function onOpen() {
  result.value = null
  if (!envId.value) envId.value = workspace.currentEnvironmentId
  loadDatabases()
}

async function run() {
  if (!props.content.trim()) return ElMessage.warning('SQL 内容为空')
  if (!connectionId.value) return ElMessage.warning('请选择数据库连接')
  try {
    await ElMessageBox.confirm(
      '将对所选连接真实执行该 SQL（若为写操作会改动数据），确认执行？',
      '二次确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  running.value = true
  try {
    result.value = await apifoxApi.debugSqlScript({
      content: props.content,
      connection_id: connectionId.value,
    })
  } finally {
    running.value = false
  }
}
</script>

<style scoped>
.sd {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
}

.sd-row {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.sd-lbl {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.sd-tip {
  margin: 0;
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-placeholder);
}

.sd-result {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}

.sd-status {
  display: flex;
  align-items: center;
  gap: var(--ax-space-2);
}

.sd-count {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
}

.sd-error {
  margin: 0;
  padding: var(--ax-space-2);
  font-size: var(--ax-text-caption-size);
  color: var(--ax-danger);
  background: var(--ax-bg-subtle);
  border-radius: var(--ax-radius-sm);
  white-space: pre-wrap;
}
</style>

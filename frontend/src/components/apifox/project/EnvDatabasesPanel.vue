<template>
  <div class="db-panel">
    <div class="db-head">
      <span class="db-title">数据库连接</span>
      <el-button size="small" type="primary" @click="openDialog()">+ 新建连接</el-button>
    </div>
    <p class="db-tip">供场景「数据库操作」步骤造数/清理/取数；密码只写不回显。当前仅 MySQL。</p>

    <el-table :data="databases" size="small" border>
      <el-table-column prop="name" label="名称" min-width="120" />
      <el-table-column label="地址" min-width="160">
        <template #default="{ row }">{{ row.host }}:{{ row.port }} / {{ row.database }}</template>
      </el-table-column>
      <el-table-column prop="username" label="用户" width="100" />
      <el-table-column label="密码" width="60" align="center">
        <template #default="{ row }">{{ row.has_password ? '●' : '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="168" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link size="small" :loading="testingId === row.id" @click="testConn(row)"
            >测试</el-button
          >
          <el-button link type="primary" size="small" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="delConn(row)">删</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="databases.length === 0" description="暂无数据库连接" :image-size="50" />

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑连接' : '新建连接'" width="440px">
      <el-form label-width="80px">
        <el-form-item label="名称"
          ><el-input v-model="form.name" :maxlength="TITLE_MAX_LEN"
        /></el-form-item>
        <el-form-item label="Host"
          ><el-input v-model="form.host" :maxlength="URL_MAX_LEN"
        /></el-form-item>
        <el-form-item label="端口"
          ><el-input-number v-model="form.port" :min="1" :max="65535"
        /></el-form-item>
        <el-form-item label="数据库"
          ><el-input v-model="form.database" :maxlength="VALUE_MAX_LEN"
        /></el-form-item>
        <el-form-item label="用户名"
          ><el-input v-model="form.username" :maxlength="TITLE_MAX_LEN"
        /></el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            :maxlength="SECRET_MAX_LEN"
            type="password"
            show-password
            placeholder="请输入密码"
            @focus="onPasswordFocus"
            @blur="onPasswordBlur"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :loading="testingDialog" @click="testDialogConn">测试连接</el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { SECRET_MAX_LEN, TITLE_MAX_LEN, URL_MAX_LEN, VALUE_MAX_LEN } from '@/constants/limits'
import { reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'

const props = defineProps<{ environmentId: Id }>()
const emit = defineEmits<{ updated: [] }>()

type DatabaseOut = Schemas['DatabaseOut']

/** 编辑态占位：服务端不回显明文，用掩码表示「已配置」 */
const PASSWORD_MASK = '******'

interface DatabaseForm {
  id: number | null
  name: string
  host: string
  port: number
  database: string
  username: string
  password: string
}

const databases = ref<DatabaseOut[]>([])
const dialogVisible = ref(false)
const saving = ref(false)
const testingId = ref<number | null>(null)
const testingDialog = ref(false)
/** 打开编辑弹窗时是否已有保存的密码（用于判定掩码/留空是否表示不修改） */
const editingHadPassword = ref(false)
const form = reactive<DatabaseForm>({
  id: null,
  name: '',
  host: '',
  port: 3306,
  database: '',
  username: '',
  password: '',
})

async function load() {
  databases.value = props.environmentId ? await apifoxApi.listDatabases(props.environmentId) : []
}

watch(() => props.environmentId, load, { immediate: true })

function isPasswordUnchanged(): boolean {
  if (!form.id) return false
  if (form.password === PASSWORD_MASK) return true
  return editingHadPassword.value && !form.password
}

function onPasswordFocus() {
  if (form.id && form.password === PASSWORD_MASK) form.password = ''
}

function onPasswordBlur() {
  if (form.id && editingHadPassword.value && !form.password) form.password = PASSWORD_MASK
}

function openDialog(row?: DatabaseOut) {
  editingHadPassword.value = row?.has_password ?? false
  Object.assign(form, {
    id: row?.id ?? null,
    name: row?.name ?? '',
    host: row?.host ?? '',
    port: row?.port ?? 3306,
    database: row?.database ?? '',
    username: row?.username ?? '',
    password: editingHadPassword.value ? PASSWORD_MASK : '',
  })
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) return ElMessage.warning('请填写名称')
  saving.value = true
  try {
    const payload: Schemas['DatabaseCreate'] & { password?: string } = {
      name: form.name,
      db_type: 'mysql',
      host: form.host,
      port: form.port,
      database: form.database,
      username: form.username,
    }
    // 密码：新建空=不设；编辑掩码/留空=保持原值（不下发 password）
    if (!isPasswordUnchanged() && form.password) payload.password = form.password
    if (form.id) await apifoxApi.updateDatabase(form.id, payload)
    else await apifoxApi.createDatabase(props.environmentId, payload)
    ElMessage.success('已保存')
    dialogVisible.value = false
    await load()
    emit('updated')
  } finally {
    saving.value = false
  }
}

async function testConn(row: DatabaseOut) {
  testingId.value = row.id
  try {
    const r = await apifoxApi.testDatabase(row.id)
    if (r.passed) ElMessage.success('连接成功')
    else ElMessage.error(`连接失败：${r.message}`)
  } finally {
    testingId.value = null
  }
}

// 弹窗内测试：用当前表单值探测（保存前）；编辑态未改密码则测已保存连接
async function testDialogConn() {
  if (!form.host.trim()) return ElMessage.warning('请先填写 Host')
  testingDialog.value = true
  try {
    const r =
      form.id && isPasswordUnchanged()
        ? await apifoxApi.testDatabase(form.id)
        : await apifoxApi.testDatabaseConfig(props.environmentId, {
            name: form.name,
            db_type: 'mysql',
            host: form.host,
            port: form.port,
            database: form.database,
            username: form.username,
            password: form.password,
          })
    if (r.passed) ElMessage.success('连接成功')
    else ElMessage.error(`连接失败：${r.message}`)
  } finally {
    testingDialog.value = false
  }
}

async function delConn(row: DatabaseOut) {
  await ElMessageBox.confirm(`确认删除连接「${row.name}」？`, '提示', { type: 'warning' })
  await apifoxApi.deleteDatabase(row.id)
  ElMessage.success('已删除')
  await load()
  emit('updated')
}

defineExpose({ openCreateDialog: () => openDialog() })
</script>

<style scoped>
.db-panel {
  margin-top: var(--ax-space-5);
}

.db-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ax-space-1);
}

.db-title {
  font-weight: 600;
  color: var(--ax-brand);
}

.db-tip {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-caption-size);
  margin: var(--ax-space-1) 0 var(--ax-space-2);
}
</style>

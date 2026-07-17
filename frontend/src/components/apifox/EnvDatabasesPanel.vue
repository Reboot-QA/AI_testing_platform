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
      <el-table-column label="操作" width="150" align="center">
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
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="Host"><el-input v-model="form.host" /></el-form-item>
        <el-form-item label="端口"
          ><el-input-number v-model="form.port" :min="1" :max="65535"
        /></el-form-item>
        <el-form-item label="数据库"><el-input v-model="form.database" /></el-form-item>
        <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="form.id ? '留空则不修改' : ''"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'

const props = defineProps({
  environmentId: { type: [String, Number], required: true },
})

const databases = ref([])
const dialogVisible = ref(false)
const saving = ref(false)
const testingId = ref(null)
const form = reactive({
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

function openDialog(row) {
  Object.assign(form, {
    id: row?.id ?? null,
    name: row?.name ?? '',
    host: row?.host ?? '',
    port: row?.port ?? 3306,
    database: row?.database ?? '',
    username: row?.username ?? '',
    password: '',
  })
  dialogVisible.value = true
}

async function save() {
  if (!form.name.trim()) return ElMessage.warning('请填写名称')
  saving.value = true
  try {
    const payload = {
      name: form.name,
      host: form.host,
      port: form.port,
      database: form.database,
      username: form.username,
    }
    // 密码留空：新建=不设；编辑=保持原值（不下发 password 字段）
    if (form.password) payload.password = form.password
    if (form.id) await apifoxApi.updateDatabase(form.id, payload)
    else await apifoxApi.createDatabase(props.environmentId, payload)
    ElMessage.success('已保存')
    dialogVisible.value = false
    await load()
  } finally {
    saving.value = false
  }
}

async function testConn(row) {
  testingId.value = row.id
  try {
    const r = await apifoxApi.testDatabase(row.id)
    if (r.passed) ElMessage.success('连接成功')
    else ElMessage.error(`连接失败：${r.message}`)
  } finally {
    testingId.value = null
  }
}

async function delConn(row) {
  await ElMessageBox.confirm(`确认删除连接「${row.name}」？`, '提示', { type: 'warning' })
  await apifoxApi.deleteDatabase(row.id)
  ElMessage.success('已删除')
  await load()
}
</script>

<style scoped>
.db-panel {
  margin-top: 20px;
}

.db-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.db-title {
  font-weight: 600;
  color: var(--ax-brand);
}

.db-tip {
  color: var(--ax-text-placeholder);
  font-size: 12px;
  margin: 4px 0 10px;
}
</style>

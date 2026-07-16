<template>
  <el-alert
    title="同部门用户共享项目、需求、用例等数据；管理员可查看所有部门数据。"
    type="info"
    :closable="false"
    show-icon
    class="tip-alert"
  />

  <PageCard>
    <template #toolbar>
      <el-button type="primary" @click="openDialog()">
        <el-icon><Plus /></el-icon> 添加部门
      </el-button>
    </template>

    <el-table v-loading="loading" :data="departments" stripe border>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="部门名称" min-width="160" />
      <el-table-column prop="description" label="描述" min-width="240" show-overflow-tooltip>
        <template #default="{ row }">{{ row.description || '-' }}</template>
      </el-table-column>
      <el-table-column prop="user_count" label="用户数" width="90" align="center" />
      <el-table-column prop="project_count" label="项目数" width="90" align="center" />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑部门' : '添加部门'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="部门名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入部门名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </PageCard>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { departmentApi } from '@/api'
import PageCard from '@/components/PageCard.vue'

const departments = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const editing = ref(null)
const formRef = ref()

const form = reactive({
  name: '',
  description: '',
})

const rules = {
  name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }],
}

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

async function loadData() {
  loading.value = true
  try {
    departments.value = await departmentApi.list()
  } finally {
    loading.value = false
  }
}

function openDialog(row = null) {
  editing.value = row
  form.name = row?.name || ''
  form.description = row?.description || ''
  dialogVisible.value = true
}

async function handleSubmit() {
  await formRef.value.validate()
  submitting.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
    }
    if (editing.value) {
      await departmentApi.update(editing.value.id, payload)
      ElMessage.success('更新成功')
    } else {
      await departmentApi.create(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(
    `确认删除部门「${row.name}」？若部门下仍有用户或项目将无法删除。`,
    '提示',
    { type: 'warning' },
  )
  await departmentApi.delete(row.id)
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.tip-alert {
  margin-bottom: 16px;
}
</style>

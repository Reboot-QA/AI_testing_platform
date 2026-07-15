<template>
  <div>
    <div class="toolbar">
      <el-button type="primary" data-assistant="projects.create_btn" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新建项目
      </el-button>
    </div>

    <el-table v-loading="loading" :data="projects" stripe border>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="项目名称" min-width="180" />
      <el-table-column prop="description" label="描述" min-width="240" show-overflow-tooltip />
      <el-table-column prop="requirement_count" label="需求数" width="90" align="center" />
      <el-table-column prop="testcase_count" label="用例数" width="90" align="center" />
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
            {{ row.status === 'active' ? '进行中' : row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="owner_name" label="创建人" width="100" />
      <el-table-column prop="department_name" label="部门" width="120">
        <template #default="{ row }">{{ row.department_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button
            link
            type="danger"
            :disabled="row.requirement_count > 0 || row.testcase_count > 0"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑项目' : '新建项目'" width="500px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="form.name"
            data-assistant="projects.form.name"
            placeholder="项目名称"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            data-assistant="projects.form.description"
            type="textarea"
            :rows="3"
            placeholder="项目描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          data-assistant="projects.form.submit"
          :loading="submitting"
          @click="handleSubmit"
        >
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { projectApi } from '@/api'

const projects = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const editing = ref(null)
const formRef = ref()

const form = reactive({ name: '', description: '' })
const rules = { name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }] }

function formatDate(d) {
  return d ? new Date(d).toLocaleString('zh-CN') : ''
}

async function loadData() {
  loading.value = true
  try {
    projects.value = await projectApi.list()
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
    if (editing.value) {
      await projectApi.update(editing.value.id, { name: form.name, description: form.description })
      ElMessage.success('更新成功')
    } else {
      await projectApi.create({ name: form.name, description: form.description })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  if (row.requirement_count > 0 || row.testcase_count > 0) {
    ElMessage.warning(
      `该项目下存在 ${row.requirement_count} 条需求、${row.testcase_count} 条用例，请先清理全部关联需求和用例后再删除`,
    )
    return
  }

  await ElMessageBox.confirm('确认删除该项目？', '确认删除', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
  await projectApi.delete(row.id)
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}
</style>

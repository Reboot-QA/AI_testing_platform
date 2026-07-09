<template>
  <div>
    <div class="toolbar">
      <span class="hint">选择一个项目进入接口自动化工作区</span>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建项目
      </el-button>
    </div>

    <div v-loading="loading" class="grid">
      <el-card
        v-for="p in projects"
        :key="p.id"
        class="project-card"
        shadow="hover"
        @click="enter(p.id)"
      >
        <div class="card-title">{{ p.name }}</div>
        <div class="card-desc">{{ p.description || '暂无描述' }}</div>
        <div class="card-meta">
          <el-tag size="small" type="info">需求 {{ p.requirement_count }}</el-tag>
          <el-tag size="small" type="info">用例 {{ p.testcase_count }}</el-tag>
        </div>
        <div class="card-foot">
          <span>{{ p.owner_name || '-' }}</span>
          <span>{{ formatTime(p.created_at) }}</span>
        </div>
      </el-card>

      <el-empty v-if="!loading && projects.length === 0" description="暂无可访问的项目" />
    </div>

    <el-dialog v-model="createVisible" title="新建项目" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="项目名" prop="name">
          <el-input v-model="form.name" placeholder="请输入项目名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { projectApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'

const router = useRouter()
const store = useWorkspaceStore()

const loading = ref(false)
const projects = computed(() => store.projects)

const createVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const form = reactive({ name: '', description: '' })
const rules = {
  name: [{ required: true, message: '请输入项目名', trigger: 'blur' }],
}

function formatTime(value) {
  return value ? new Date(value).toLocaleDateString('zh-CN') : '-'
}

async function loadData() {
  loading.value = true
  try {
    await store.loadProjects()
  } finally {
    loading.value = false
  }
}

function enter(id) {
  router.push(`/apifox/project/${id}`)
}

function openCreate() {
  form.name = ''
  form.description = ''
  createVisible.value = true
}

async function handleCreate() {
  await formRef.value.validate()
  submitting.value = true
  try {
    await projectApi.create({ name: form.name, description: form.description || undefined })
    ElMessage.success('创建成功')
    createVisible.value = false
    await loadData()
  } finally {
    submitting.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.hint {
  color: #64748b;
  font-size: 13px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  min-height: 120px;
}

.project-card {
  cursor: pointer;
  transition: transform 0.15s;
}

.project-card:hover {
  transform: translateY(-2px);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a365d;
  margin-bottom: 8px;
}

.card-desc {
  color: #64748b;
  font-size: 13px;
  height: 40px;
  overflow: hidden;
  margin-bottom: 12px;
}

.card-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.card-foot {
  display: flex;
  justify-content: space-between;
  color: #94a3b8;
  font-size: 12px;
}
</style>

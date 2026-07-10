<template>
  <div v-loading="loading" class="workbench">
    <WorkbenchStats :projects="projects" />

    <div class="quick-row">
      <div class="quick-card primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        <span>新建项目</span>
      </div>
      <div v-if="lastProject" class="quick-card" @click="enter(lastProject.id)">
        <el-icon><Position /></el-icon>
        <span>继续上次：{{ lastProject.name }}</span>
      </div>
    </div>

    <section v-if="recentCards.length" class="block">
      <h3 class="block-title">最近访问</h3>
      <div class="grid">
        <ProjectCard
          v-for="r in recentCards"
          :key="r.project.id"
          :project="r.project"
          :visited-at="r.at"
          @enter="enter"
        />
      </div>
    </section>

    <section class="block">
      <div class="block-head">
        <h3 class="block-title">全部项目</h3>
        <el-input
          v-model="keyword"
          size="small"
          clearable
          placeholder="搜索项目名称"
          class="search"
        />
      </div>
      <div class="grid">
        <ProjectCard
          v-for="p in filteredProjects"
          :key="p.id"
          :project="p"
          @enter="enter"
        />
      </div>
      <el-empty v-if="!loading && filteredProjects.length === 0" :description="emptyText" />
    </section>

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
import { useRecentProjects } from '@/composables/useRecentProjects'
import WorkbenchStats from '@/components/apifox/workbench/WorkbenchStats.vue'
import ProjectCard from '@/components/apifox/workbench/ProjectCard.vue'

const router = useRouter()
const store = useWorkspaceStore()
const { list: recentList } = useRecentProjects()

const loading = ref(false)
const keyword = ref('')
const projects = computed(() => store.projects)

// 最近访问记录与现存项目对齐：过滤已删除、附最新计数
const recentCards = computed(() =>
  recentList()
    .map((r) => ({ at: r.at, project: projects.value.find((p) => p.id === r.id) }))
    .filter((r) => r.project)
)

const lastProject = computed(() => recentCards.value[0]?.project || null)

const filteredProjects = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return projects.value
  return projects.value.filter((p) => (p.name || '').toLowerCase().includes(kw))
})

const emptyText = computed(() => (keyword.value.trim() ? '没有匹配的项目' : '暂无可访问的项目'))

const createVisible = ref(false)
const submitting = ref(false)
const formRef = ref()
const form = reactive({ name: '', description: '' })
const rules = {
  name: [{ required: true, message: '请输入项目名', trigger: 'blur' }],
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
.block {
  margin-top: 24px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.block-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ax-text);
  margin: 0 0 12px;
}

.block-head .block-title {
  margin: 0;
}

.search {
  width: 220px;
}

.quick-row {
  display: flex;
  gap: 16px;
}

.quick-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 22px;
  border: 1px dashed var(--ax-border);
  border-radius: var(--ax-radius-lg);
  color: var(--ax-text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.quick-card:hover {
  border-color: var(--ax-brand);
  color: var(--ax-brand);
}

.quick-card.primary {
  border-style: solid;
  border-color: var(--ax-brand);
  color: var(--ax-brand);
  font-weight: 600;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
  min-height: 80px;
}
</style>

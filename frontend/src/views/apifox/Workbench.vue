<template>
  <div v-loading="loading" class="workbench">
    <WorkbenchStats :stats="overview.stats" />

    <div class="dash-grid">
      <div class="card projects-card">
        <div class="card-h">
          我的项目
          <el-button type="primary" size="small" @click="openCreate">
            <el-icon><Plus /></el-icon> 新建项目
          </el-button>
        </div>
        <div class="projgrid-wrap">
          <div class="projgrid">
            <DashboardProjectCard
              v-for="p in overview.projects"
              :key="p.id"
              :project="p"
              @enter="enter"
            />
            <div class="projcard newcard" @click="openCreate">
              <div class="plus">＋</div>
              新建项目
            </div>
          </div>
          <el-empty
            v-if="!loading && !overview.projects.length"
            description="暂无可访问的项目"
            :image-size="60"
          />
        </div>
      </div>

      <div class="side-col">
        <RunningAutomations :running="overview.running" @open="openReports" />
        <RecentReports :reports="overview.recent_reports" @open="openReports" />
      </div>
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
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apifoxApi, projectApi } from '@/api'
import WorkbenchStats from '@/components/apifox/workbench/WorkbenchStats.vue'
import DashboardProjectCard from '@/components/apifox/workbench/DashboardProjectCard.vue'
import RunningAutomations from '@/components/apifox/workbench/RunningAutomations.vue'
import RecentReports from '@/components/apifox/workbench/RecentReports.vue'

const router = useRouter()

const loading = ref(false)
const overview = reactive({ stats: {}, projects: [], running: [], recent_reports: [] })

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
    const data = await apifoxApi.workbenchOverview()
    Object.assign(overview, data)
  } catch {
    // 全局响应拦截器已提示错误；此处仅避免 onMounted 未捕获的 rejection
  } finally {
    loading.value = false
  }
}

function enter(id) {
  router.push(`/apifox/project/${id}`)
}

function openReports(run) {
  router.push(`/apifox/project/${run.project_id}/reports`)
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
.dash-grid {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 16px;
  align-items: start;
}

@media (max-width: 900px) {
  .dash-grid { grid-template-columns: 1fr; }
}

.card {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
}

.card-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--ax-border);
  font-weight: 600;
}

.projgrid-wrap {
  padding: 14px;
}

.projgrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 14px;
}

.projcard.newcard {
  border: 1px dashed var(--ax-border);
  border-radius: var(--ax-radius-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: var(--ax-text-tertiary);
  cursor: pointer;
  min-height: 118px;
  transition: all 0.15s;
}

.projcard.newcard:hover {
  color: var(--ax-brand);
  border-color: var(--ax-brand);
}

.plus { font-size: 24px; }

.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>

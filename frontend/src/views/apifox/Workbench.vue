<template>
  <div v-loading="loading" class="workbench">
    <WorkbenchStats :stats="overview.stats" />

    <div class="dash-grid">
      <div class="card projects-card">
        <div class="card-h">
          <span class="card-title"
            ><el-icon><Folder /></el-icon> 我的项目</span
          >
          <el-button type="primary" size="small" @click="openCreate">
            <el-icon><Plus /></el-icon> 新建项目
          </el-button>
        </div>
        <div class="projgrid-wrap">
          <div class="projgrid">
            <VueDraggable
              v-model="overview.projects"
              :animation="150"
              handle=".drag-handle"
              style="display: contents"
              @end="persistOrder"
            >
              <DashboardProjectCard
                v-for="p in overview.projects"
                :key="p.id"
                :project="p"
                @enter="enter"
                @rename="handleRename"
                @delete="handleDelete"
                @pin="handlePin"
              />
            </VueDraggable>
            <div class="projcard newcard" @click="openCreate">
              <div class="plus">
                <el-icon><Plus /></el-icon>
              </div>
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

      <WorkbenchActivity
        ref="activityRef"
        :running-count="overview.stats.running_count ?? 0"
        @open="openReports"
      />
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

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { VueDraggable } from 'vue-draggable-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi, projectApi } from '@/api'
import WorkbenchStats from '@/components/apifox/workbench/WorkbenchStats.vue'
import DashboardProjectCard from '@/components/apifox/workbench/DashboardProjectCard.vue'
import WorkbenchActivity from '@/components/apifox/workbench/WorkbenchActivity.vue'

const router = useRouter()

const loading = ref(false)
const activityRef = ref<{ refresh: () => Promise<void> } | null>(null)
const overview = reactive<Schemas['WorkbenchOverviewOut']>({
  stats: {} as Schemas['WorkbenchStats'],
  projects: [],
})

const createVisible = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '' })
const rules: FormRules = {
  name: [{ required: true, message: '请输入项目名', trigger: 'blur' }],
}

async function loadData() {
  loading.value = true
  try {
    const data = await apifoxApi.workbenchOverview()
    Object.assign(overview, data)
    await activityRef.value?.refresh()
  } catch {
    // 全局响应拦截器已提示错误；此处仅避免 onMounted 未捕获的 rejection
  } finally {
    loading.value = false
  }
}

function enter(id: number) {
  router.push(`/apifox/project/${id}`)
}

// 置顶项稳定置于最前（与后端排序语义一致），再按当前展示顺序保存偏好
async function persistOrder() {
  overview.projects.sort((a, b) => Number(b.pinned) - Number(a.pinned))
  const items = overview.projects.map((p) => ({ project_id: p.id, pinned: !!p.pinned }))
  try {
    await projectApi.savePreferences(items)
  } catch {
    // 保存失败：全局拦截器已提示；乐观改动可能已生效，重载后端真值避免本地漂移
    await loadData()
  }
}

function handlePin(project: Schemas['WorkbenchProject']) {
  project.pinned = !project.pinned
  persistOrder()
}

function openReports(run: Schemas['WorkbenchRunning'] | Schemas['WorkbenchReport']) {
  router.push(`/apifox/project/${run.project_id}/reports`)
}

function openCreate() {
  form.name = ''
  form.description = ''
  createVisible.value = true
}

async function handleCreate() {
  await formRef.value?.validate()
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

async function handleRename(project: Schemas['WorkbenchProject']) {
  const { value } = await ElMessageBox.prompt('项目名称', '重命名项目', {
    inputValue: project.name,
    inputPattern: /\S/,
    inputErrorMessage: '项目名不能为空',
  })
  const name = value.trim()
  if (name === project.name) return
  await projectApi.update(project.id, { name })
  ElMessage.success('已重命名')
  await loadData()
}

async function handleDelete(project: Schemas['WorkbenchProject']) {
  // 硬删除不可逆：要求输入项目名完全一致二次确认
  await ElMessageBox.prompt(
    `此操作将永久删除项目「${project.name}」及其全部数据（接口、场景、用例、需求、运行报告等），不可恢复！\n请输入项目名称以确认：`,
    '硬删除项目',
    {
      type: 'warning',
      confirmButtonText: '确认删除',
      confirmButtonClass: 'el-button--danger',
      inputValidator: (v) => (v || '').trim() === project.name || '项目名称不一致',
    },
  )
  await projectApi.delete(project.id)
  ElMessage.success('已删除')
  await loadData()
}

onMounted(loadData)
</script>

<style scoped>
/* 撑满可视区域：顶栏 60px + main 上下 padding 40px */
.workbench {
  height: calc(100vh - 100px);
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.dash-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 12px;
  align-items: stretch;
}

@media (max-width: 900px) {
  .dash-grid {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }

  .workbench {
    overflow: auto;
  }
}

.card {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
}

.projects-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.card-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--ax-border);
  font-weight: 600;
  flex: none;
}

.card-title {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.card-title .el-icon {
  color: var(--ax-brand);
}

.projgrid-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 12px;
}

.projgrid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
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
  min-height: 92px;
  font-size: 13px;
  transition: all var(--ax-transition);
}

.projcard.newcard:hover {
  color: var(--ax-brand);
  border-color: var(--ax-brand);
  background: var(--ax-brand-subtle);
}

.plus {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 18px;
  color: var(--ax-brand);
  background: var(--ax-brand-subtle);
  transition: all var(--ax-transition);
}

.projcard.newcard:hover .plus {
  background: var(--ax-brand);
  color: #fff;
}
</style>

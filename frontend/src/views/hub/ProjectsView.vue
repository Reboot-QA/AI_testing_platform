<template>
  <div v-loading="loading" class="projects-view">
    <StatTiles :stats="overview.stats" />

    <div class="toolbar">
      <el-radio-group v-model="segment">
        <el-radio-button value="all">全部</el-radio-button>
        <!-- <el-radio-button value="mine">我参与的</el-radio-button> -->
        <el-radio-button value="pinned">置顶</el-radio-button>
      </el-radio-group>
      <el-input
        v-model="keyword"
        :maxlength="SEARCH_MAX_LEN"
        clearable
        placeholder="搜索项目名 / 描述 / 负责人"
        class="search"
      >
        <template #prefix
          ><el-icon><Search /></el-icon
        ></template>
      </el-input>
      <div class="spacer" />
      <el-button type="primary" data-assistant="projects.create_btn" @click="openCreate">
        <el-icon><Plus /></el-icon> 新建项目
      </el-button>
    </div>

    <div class="body">
      <div class="proj-panel">
        <div class="panel-head">
          <div class="panel-title">我的项目</div>
          <span class="panel-count">{{ filtered.length }} 个</span>
        </div>
        <div class="grid-wrap">
          <div class="grid">
            <ProjectCard
              v-for="p in filtered"
              :key="p.id"
              :project="p"
              @enter="enter"
              @pin="handlePin"
              @rename="handleRename"
              @edit="openEdit"
              @delete="handleDelete"
            />
            <div class="newcard" @click="openCreate">
              <div class="plus">
                <el-icon><Plus /></el-icon>
              </div>
              新建项目
            </div>
          </div>
          <el-empty
            v-if="!loading && !filtered.length"
            description="没有匹配的项目"
            :image-size="60"
          />
        </div>
      </div>

      <ActivitySide ref="activityRef" @open="openReports" />
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑项目' : '新建项目'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="项目名" prop="name">
          <el-input
            v-model="form.name"
            :maxlength="TITLE_MAX_LEN"
            data-assistant="projects.form.name"
            placeholder="请输入项目名称"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            :maxlength="DESC_MAX_LEN"
            data-assistant="projects.form.description"
            type="textarea"
            :rows="3"
            placeholder="选填"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          data-assistant="projects.form.submit"
          @click="submitProject"
        >
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { nameInputOptions } from '@/utils/promptLimits'
import { DESC_MAX_LEN, SEARCH_MAX_LEN, TITLE_MAX_LEN } from '@/constants/limits'
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormItemRule, FormRules } from 'element-plus'
import type { Schemas } from '@/api/types'
import { apifoxApi, projectApi } from '@/api'
import type { WorkspaceDomain } from '@/types/shell'
import {
  registerAssistantHandler,
  unregisterAssistantHandler,
} from '@/utils/assistantActionRegistry'
import StatTiles from '@/components/hub/StatTiles.vue'
import ProjectCard from '@/components/hub/ProjectCard.vue'
import ActivitySide from '@/components/hub/ActivitySide.vue'

type WorkbenchProject = Schemas['WorkbenchProject']

const router = useRouter()
const loading = ref(false)
const activityRef = ref<{ refresh: () => Promise<void> } | null>(null)
const overview = reactive<Schemas['WorkbenchOverviewOut']>({
  stats: {} as Schemas['WorkbenchStats'],
  projects: [],
})

const segment = ref<'all' | 'mine' | 'pinned'>('all')
const keyword = ref('')

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return overview.projects.filter((p) => {
    // 我参与的：P0 阶段后端返回的均为可访问项目，暂等同全部；待后端补 is_member 标记再细分
    if (segment.value === 'pinned' && !p.pinned) return false
    if (!kw) return true
    return `${p.name} ${p.description ?? ''} ${p.role}`.toLowerCase().includes(kw)
  })
})

const dialogVisible = ref(false)
const submitting = ref(false)
const editing = ref<WorkbenchProject | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', description: '' })

function isDuplicateProjectName(name: string, excludeId?: number) {
  const normalized = name.trim()
  return overview.projects.some((p) => p.name.trim() === normalized && p.id !== excludeId)
}

const validateUniqueProjectName: NonNullable<FormItemRule['validator']> = (
  _rule,
  value,
  callback,
) => {
  const name = String(value || '').trim()
  if (!name) {
    callback(new Error('请输入项目名'))
    return
  }
  if (isDuplicateProjectName(name, editing.value?.id)) {
    callback(new Error('项目名称已存在'))
    return
  }
  callback()
}

const rules: FormRules = {
  name: [
    { required: true, message: '请输入项目名', trigger: 'blur' },
    { max: 100, message: '项目名不超过 100 个字符', trigger: 'blur' },
    { validator: validateUniqueProjectName, trigger: 'blur' },
  ],
  description: [{ max: 500, message: '描述不超过 500 个字符', trigger: 'blur' }],
}

async function loadData() {
  loading.value = true
  try {
    const data = await apifoxApi.workbenchOverview()
    Object.assign(overview, data)
    await activityRef.value?.refresh()
  } catch {
    // 全局拦截器已提示
  } finally {
    loading.value = false
  }
}

function enter(id: number, domain: WorkspaceDomain = 'requirements') {
  const section = domain === 'requirements' ? '&section=req-overview' : ''
  router.push({ path: `/hub/workspace/${id}`, hash: `#domain=${domain}${section}` })
}

function openReports(projectId: number) {
  router.push({
    path: `/hub/workspace/${projectId}`,
    hash: `#domain=automation&biz=reports&section=reports`,
  })
}

async function persistOrder() {
  try {
    await projectApi.savePreferences(
      overview.projects.map((p) => ({ project_id: p.id, pinned: !!p.pinned })),
    )
  } catch {
    await loadData()
  }
}

function handlePin(project: WorkbenchProject) {
  const idx = overview.projects.indexOf(project)
  if (idx < 0) return
  project.pinned = !project.pinned
  overview.projects.splice(idx, 1)
  if (project.pinned) {
    overview.projects.unshift(project)
  } else {
    const insertAt = overview.projects.findIndex((p) => !p.pinned)
    if (insertAt === -1) overview.projects.push(project)
    else overview.projects.splice(insertAt, 0, project)
  }
  void persistOrder()
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.description = ''
  dialogVisible.value = true
}

function openEdit(project: WorkbenchProject) {
  editing.value = project
  form.name = project.name
  form.description = project.description ?? ''
  dialogVisible.value = true
}

async function submitProject(): Promise<Schemas['ProjectOut']> {
  await formRef.value?.validate()
  submitting.value = true
  try {
    let saved: Schemas['ProjectOut']
    if (editing.value) {
      saved = await projectApi.update(editing.value.id, {
        name: form.name,
        description: form.description || undefined,
      })
      ElMessage.success('已保存')
    } else {
      saved = await projectApi.create({
        name: form.name,
        description: form.description || undefined,
      })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadData()
    return saved
  } finally {
    submitting.value = false
  }
}

async function handleRename(project: WorkbenchProject) {
  const { value } = await ElMessageBox.prompt('项目名称', '重命名项目', {
    inputValue: project.name,
    ...nameInputOptions(),
  })
  const name = value.trim()
  if (name === project.name) return
  if (isDuplicateProjectName(name, project.id)) {
    ElMessage.warning('项目名称已存在')
    return
  }
  await projectApi.update(project.id, { name })
  ElMessage.success('已重命名')
  await loadData()
}

async function handleDelete(project: WorkbenchProject) {
  await ElMessageBox.prompt(
    `此操作将永久删除项目「${project.name}」及其全部数据，不可恢复！\n请输入项目名称以确认：`,
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

onMounted(async () => {
  registerAssistantHandler('projects.prepareDemo', async (payload) => {
    openCreate()
    form.name = typeof payload?.name === 'string' ? payload.name : 'AI演示项目'
    form.description =
      typeof payload?.description === 'string' ? payload.description : '由 AI 助手创建'
    await nextTick()
  })
  registerAssistantHandler('projects.submitDemo', async (payload) => {
    if (!dialogVisible.value || editing.value) {
      throw new Error('项目创建表单尚未准备好')
    }
    const project = await submitProject()
    const requestedHash = typeof payload?.next_hash === 'string' ? payload.next_hash : ''
    const nextHash = requestedHash.startsWith('#domain=')
      ? requestedHash
      : '#domain=settings&open=basic'
    await router.push({ path: `/hub/workspace/${project.id}`, hash: nextHash })
  })
  await loadData()
})

onUnmounted(() => {
  unregisterAssistantHandler('projects.prepareDemo')
  unregisterAssistantHandler('projects.submitDemo')
})
</script>

<style scoped>
.projects-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-3);
  min-height: 0;
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: var(--ax-toolbar-gap);
  flex: none;
}

.search {
  width: 260px;
}

.spacer {
  flex: 1;
}

.body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: var(--ax-space-3);
  align-items: stretch;
}

.proj-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.panel-head {
  height: 32px;
  padding: 0 var(--ax-space-0-5);
  display: flex;
  align-items: baseline;
  gap: var(--ax-space-2);
  flex: none;
}

.panel-title {
  color: var(--ax-text);
  font-size: var(--ax-text-body-sm-size);
  font-weight: 600;
}

.panel-count {
  color: var(--ax-text-placeholder);
  font-size: var(--ax-text-caption-size);
}

.grid-wrap {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--ax-space-2) var(--ax-space-0-5) var(--ax-space-1);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--ax-space-3);
}

.newcard {
  border: 1px dashed color-mix(in srgb, var(--ax-border) 85%, var(--ax-text-placeholder));
  border-radius: var(--ax-radius-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--ax-space-1-5);
  color: var(--ax-text-secondary);
  cursor: pointer;
  height: 132px;
  background: color-mix(in srgb, var(--ax-bg) 55%, transparent);
  font-size: var(--ax-text-body-sm-size);
  transition:
    color var(--ax-transition),
    border-color var(--ax-transition),
    background var(--ax-transition);
}

.newcard:hover {
  color: var(--ax-brand);
  border-color: color-mix(in srgb, var(--ax-brand) 45%, var(--ax-border));
  background: var(--ax-brand-subtle);
}

.plus {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: var(--ax-text-title-size);
  color: var(--ax-brand);
  background: color-mix(in srgb, var(--ax-brand) 10%, white);
}

@media (max-width: 900px) {
  .body {
    grid-template-columns: 1fr;
    overflow-y: auto;
  }
}
</style>

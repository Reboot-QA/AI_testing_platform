<template>
  <div class="proj-settings">
    <div class="side-panel">
      <div
        v-for="s in SECTIONS"
        :key="s.key"
        class="side-item"
        :class="{ active: section === s.key }"
        @click="section = s.key"
      >
        <el-icon><component :is="s.icon" /></el-icon>
        <span>{{ s.label }}</span>
      </div>
    </div>

    <!-- 基本信息 -->
    <div v-if="section === 'basic'" class="editor-panel">
      <div class="basic-form">
        <div class="field">
          <span class="lbl">项目名称</span>
          <el-input v-model="basicForm.name" placeholder="项目名称" style="max-width: 360px" />
        </div>
        <div class="field">
          <span class="lbl">描述</span>
          <el-input v-model="basicForm.description" type="textarea" :rows="3" placeholder="选填" style="max-width: 360px" />
        </div>
        <el-button type="primary" :loading="savingBasic" @click="saveBasic">保存</el-button>
      </div>

      <div class="danger-zone">
        <div class="dz-title">危险区域</div>
        <div class="dz-row">
          <div>
            <div class="dz-h">删除项目</div>
            <div class="dz-desc">永久删除该项目及其全部接口 / 用例 / 场景 / 环境 / 数据模型 / 脚本 / 定时任务 / 运行记录等数据，不可恢复。</div>
          </div>
          <el-button type="danger" :disabled="hasLinkedData" @click="delProject">删除项目</el-button>
        </div>
      </div>
    </div>

    <!-- 脚本库 -->
    <template v-if="section === 'scripts'">
      <div class="list-panel">
        <div class="list-toolbar">
          <span>脚本库</span>
          <el-button size="small" type="primary" @click="addScript">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
        <div
          v-for="s in scripts"
          :key="s.id"
          class="item"
          :class="{ active: scriptForm.id === s.id }"
          @click="onSelectScript(s.id)"
        >
          <el-tag size="small" :type="s.lang === 'python' ? 'warning' : 'success'">
            {{ s.lang === 'python' ? 'Py' : 'JS' }}
          </el-tag>
          <span class="item-name">{{ s.name }}</span>
          <el-button link type="danger" size="small" @click.stop="delScript(s)">删</el-button>
        </div>
        <el-empty v-if="scripts.length === 0" description="暂无脚本" :image-size="60" />
      </div>

      <div class="editor-panel">
        <template v-if="scriptForm.id">
          <div class="row1">
            <el-input v-model="scriptForm.name" placeholder="脚本名称" style="width: 220px" />
            <el-select v-model="scriptForm.lang" style="width: 120px">
              <el-option label="JavaScript" value="javascript" />
              <el-option label="Python" value="python" />
            </el-select>
            <el-button type="primary" :loading="saving" @click="saveScript">保存</el-button>
          </div>
          <el-input v-model="scriptForm.description" placeholder="描述（选填）" class="desc-input" />
          <CodeEditor v-model="scriptForm.content" :language="scriptForm.lang" height="360px" />
        </template>
        <el-empty v-else description="选择或新建一个脚本（脚本跟随项目，可被用例前后置引用）" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi, projectApi } from '@/api'
import { useUnsavedGuard } from '@/composables/useUnsavedGuard'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'

const route = useRoute()
const router = useRouter()
const pid = computed(() => route.params.projectId)

const SECTIONS = [
  { key: 'basic', label: '基本信息', icon: 'Setting' },
  { key: 'scripts', label: '脚本库', icon: 'Tickets' },
]

const section = ref('basic')
const scripts = ref([])
const saving = ref(false)
const scriptForm = reactive({ id: null, name: '', lang: 'javascript', content: '', description: '' })

const savingBasic = ref(false)
const basicForm = reactive({ name: '', description: '' })
const requirementCount = ref(0)
const testcaseCount = ref(0)
const hasLinkedData = computed(() => requirementCount.value > 0 || testcaseCount.value > 0)

async function loadBasic() {
  const p = await projectApi.get(pid.value)
  basicForm.name = p.name
  basicForm.description = p.description || ''
  requirementCount.value = p.requirement_count || 0
  testcaseCount.value = p.testcase_count || 0
}

async function saveBasic() {
  savingBasic.value = true
  try {
    await projectApi.update(pid.value, { name: basicForm.name, description: basicForm.description || null })
    ElMessage.success('已保存')
  } finally {
    savingBasic.value = false
  }
}

async function delProject() {
  if (hasLinkedData.value) {
    ElMessage.warning(
      `该项目下存在 ${requirementCount.value} 条需求、${testcaseCount.value} 条用例，请先清理全部关联需求和用例后再删除`
    )
    return
  }

  await ElMessageBox.confirm(
    '将永久删除该项目及其全部接口/用例/场景/环境/数据模型/脚本/定时任务/运行记录等数据，不可恢复。确认删除？',
    '删除项目',
    { type: 'warning', confirmButtonText: '删除', confirmButtonClass: 'el-button--danger' },
  )
  await projectApi.delete(pid.value)
  ElMessage.success('项目已删除')
  router.push('/apifox')
}

async function loadScripts() {
  scripts.value = await apifoxApi.listScripts(pid.value)
}

// 脚本未保存保护：切脚本/切主 tab/关浏览器前，dirty 则提示
const scriptGuard = useUnsavedGuard({
  serialize: () => JSON.stringify({
    id: scriptForm.id, name: scriptForm.name, lang: scriptForm.lang,
    content: scriptForm.content, description: scriptForm.description,
  }),
  save: () => saveScript(),
  name: () => scriptForm.name,
})

async function selectScript(sid) {
  const s = await apifoxApi.getScript(sid)
  scriptForm.id = s.id
  scriptForm.name = s.name
  scriptForm.lang = s.lang
  scriptForm.content = s.content
  scriptForm.description = s.description || ''
  scriptGuard.markSaved()
}

async function onSelectScript(id) {
  if (id === scriptForm.id) return
  if (!(await scriptGuard.confirmLeave())) return
  await selectScript(id)
}

async function addScript() {
  if (!(await scriptGuard.confirmLeave())) return // 当前脚本有未保存改动时先确认
  const { value } = await ElMessageBox.prompt('脚本名称', '新建脚本', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  const created = await apifoxApi.createScript(pid.value, { name: value, lang: 'javascript', content: '' })
  ElMessage.success('已创建')
  await loadScripts()
  await selectScript(created.id)
}

async function saveScript() {
  saving.value = true
  try {
    await apifoxApi.updateScript(scriptForm.id, {
      name: scriptForm.name,
      lang: scriptForm.lang,
      content: scriptForm.content,
      description: scriptForm.description || null,
    })
    scriptGuard.markSaved()
    ElMessage.success('已保存')
    await loadScripts()
    return true
  } catch {
    return false // 后端错误已由 api 拦截器提示
  } finally {
    saving.value = false
  }
}

async function delScript(s) {
  await ElMessageBox.confirm(`确认删除脚本「${s.name}」？被用例引用时会被拦截。`, '提示', { type: 'warning' })
  await apifoxApi.deleteScript(s.id)
  if (scriptForm.id === s.id) {
    scriptForm.id = null
    scriptForm.name = ''
    scriptForm.content = ''
    scriptForm.description = ''
    scriptGuard.markSaved()
  }
  ElMessage.success('已删除')
  await loadScripts()
}

onMounted(() => {
  loadBasic()
  loadScripts()
})
</script>

<style scoped>
.proj-settings {
  display: flex;
  gap: 16px;
  height: calc(100vh - 220px);
}

.side-panel {
  width: 140px;
  border-right: 1px solid var(--ax-border);
  padding-right: 8px;
}

.side-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--ax-text-tertiary);
}

.side-item:hover {
  background: var(--ax-bg-hover);
}

.side-item.active {
  background: var(--ax-bg-active);
  color: var(--ax-brand);
  font-weight: 600;
}

.list-panel {
  width: 240px;
  border-right: 1px solid var(--ax-border);
  overflow: auto;
  padding-right: 8px;
}

.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 8px;
}

.item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.item:hover {
  background: var(--ax-bg-hover);
}

.item.active {
  background: var(--ax-bg-active);
}

.item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.editor-panel {
  flex: 1;
  overflow: auto;
}

.row1 {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.desc-input {
  margin-bottom: 10px;
}

.basic-form {
  max-width: 480px;
}

.field {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}

.lbl {
  flex-shrink: 0;
  width: 72px;
  font-size: 13px;
  color: var(--ax-text-secondary);
  padding-top: 6px;
}

.danger-zone {
  max-width: 620px;
  margin-top: 28px;
  border: 1px solid var(--ax-danger);
  border-radius: var(--ax-radius-lg);
  padding: 16px;
}

.dz-title {
  font-weight: 600;
  color: var(--ax-danger);
  margin-bottom: 12px;
}

.dz-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.dz-h {
  font-weight: 600;
}

.dz-desc {
  font-size: 12px;
  color: var(--ax-text-secondary);
  margin-top: 2px;
}
</style>

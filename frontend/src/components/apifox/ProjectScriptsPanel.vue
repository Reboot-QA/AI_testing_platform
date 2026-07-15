<template>
  <div class="scripts-panel">
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
          <el-button @click="debugVisible = true">调试</el-button>
        </div>
        <el-input v-model="scriptForm.description" placeholder="描述（选填）" class="desc-input" />
        <CodeEditor v-model="scriptForm.content" :language="scriptForm.lang" height="360px" />
      </template>
      <el-empty v-else description="选择或新建一个脚本（脚本跟随项目，可被用例前后置引用）" />
    </div>

    <ScriptDebugDialog v-model:visible="debugVisible" :lang="scriptForm.lang" :content="scriptForm.content" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import { isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useUnsavedGuard } from '@/composables/useUnsavedGuard'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'
import ScriptDebugDialog from '@/components/apifox/ScriptDebugDialog.vue'

const props = defineProps({
  projectId: { type: [String, Number], required: true },
})

const scripts = ref([])
const saving = ref(false)
const debugVisible = ref(false)
const scriptForm = reactive({ id: null, name: '', lang: 'javascript', content: '', description: '', version: 1 })

async function loadScripts() {
  scripts.value = await apifoxApi.listScripts(props.projectId)
}

// 脚本未保存保护：切脚本/关浏览器前，dirty 则提示
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
  scriptForm.version = s.version ?? 1
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
  const created = await apifoxApi.createScript(props.projectId, { name: value, lang: 'javascript', content: '' })
  ElMessage.success('已创建')
  await loadScripts()
  await selectScript(created.id)
}

async function doSaveScript() {
  const updated = await apifoxApi.updateScript(scriptForm.id, {
    name: scriptForm.name,
    lang: scriptForm.lang,
    content: scriptForm.content,
    description: scriptForm.description || null,
    expected_version: scriptForm.version,
  })
  scriptForm.version = updated.version
  await loadScripts()
}

async function saveScript() {
  saving.value = true
  try {
    await doSaveScript()
    scriptGuard.markSaved()
    ElMessage.success('已保存')
    return true
  } catch (e) {
    if (!isConflict(e)) return false // 非冲突错误已由 api 拦截器提示
    let resolved = false
    await resolveSaveConflict({
      reload: async () => {
        await selectScript(scriptForm.id)
        resolved = true
      },
      overwrite: async () => {
        const latest = await apifoxApi.getScript(scriptForm.id)
        scriptForm.version = latest.version
        await doSaveScript()
        scriptGuard.markSaved()
        resolved = true
      },
    })
    return resolved
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
    scriptForm.version = 1
    scriptGuard.markSaved()
  }
  ElMessage.success('已删除')
  await loadScripts()
}

onMounted(loadScripts)
</script>

<style scoped>
.scripts-panel {
  display: flex;
  gap: 16px;
  flex: 1;
  min-width: 0;
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
</style>

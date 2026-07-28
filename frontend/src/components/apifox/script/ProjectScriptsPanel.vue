<template>
  <div class="scripts-panel h-full">
    <div class="list-panel h-full">
      <div class="list-toolbar">
        <span>脚本库</span>
        <el-button type="primary" size="small" @click="addScript">
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

    <div class="editor-panel h-full flex flex-col">
      <div
        v-if="isDraft || scriptForm.id"
        :key="scriptForm.id ?? 'draft'"
        class="editor-body flex flex-1 flex-col min-h-0"
      >
        <div class="row1">
          <el-input
            v-model="scriptForm.name"
            placeholder="脚本名称（保存前填写）"
            :maxlength="TITLE_MAX_LEN"
            style="width: 220px"
          />
          <el-select v-model="scriptForm.lang" style="width: 120px">
            <el-option label="JavaScript" value="javascript" />
            <el-option label="Python" value="python" />
          </el-select>
          <el-button type="primary" :loading="saving" @click="saveScript">保存</el-button>
          <el-button @click="debugVisible = true">调试</el-button>
          <el-tag v-if="isDraft" size="small" type="info">未保存草稿</el-tag>
        </div>
        <el-input
          v-model="scriptForm.description"
          placeholder="描述（选填）"
          :maxlength="DESC_MAX_LEN"
          show-word-limit
          class="desc-input"
        />
        <CodeEditor
          v-model="scriptForm.content"
          :language="scriptForm.lang"
          height=""
          class="flex-1"
        />
      </div>
      <el-empty v-else description="选择或新建一个脚本（脚本跟随项目，可被用例前后置引用）" />
    </div>

    <ScriptDebugDialog
      v-model:visible="debugVisible"
      :project-id="projectId"
      :lang="scriptForm.lang"
      :content="scriptForm.content"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Id } from '@/api/request'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { DESC_MAX_LEN, TITLE_MAX_LEN } from '@/constants/limits'
import { isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { useUnsavedGuard } from '@/composables/useUnsavedGuard'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'
import ScriptDebugDialog from '@/components/apifox/script/ScriptDebugDialog.vue'

const props = defineProps<{ projectId: Id }>()

const scripts = ref<Schemas['ScriptBrief'][]>([])
const saving = ref(false)
const debugVisible = ref(false)
const isDraft = ref(false) // 草稿态：新建脚本先写代码/调试，保存时才落库
const scriptForm = reactive({
  id: null as number | null,
  name: '',
  lang: 'javascript',
  content: '',
  description: '',
  version: 1,
})

async function loadScripts() {
  scripts.value = await apifoxApi.listScripts(props.projectId)
}

// 脚本未保存保护：切脚本/关浏览器前，dirty 则提示
const scriptGuard = useUnsavedGuard({
  serialize: () =>
    JSON.stringify({
      id: scriptForm.id,
      name: scriptForm.name,
      lang: scriptForm.lang,
      content: scriptForm.content,
      description: scriptForm.description,
    }),
  save: () => saveScript(),
  name: () => scriptForm.name,
})

async function selectScript(sid: Id) {
  const s = await apifoxApi.getScript(sid)
  isDraft.value = false
  scriptForm.id = s.id
  scriptForm.name = s.name
  scriptForm.lang = s.lang
  scriptForm.content = s.content
  scriptForm.description = s.description || ''
  scriptForm.version = s.version ?? 1
  scriptGuard.markSaved()
}

async function onSelectScript(id: number) {
  if (id === scriptForm.id) return
  if (!(await scriptGuard.confirmLeave())) return
  await selectScript(id)
}

async function addScript() {
  if (!(await scriptGuard.confirmLeave())) return // 当前脚本有未保存改动时先确认
  // 进入草稿态：先写代码、调试，最后再填名称/描述一起保存（此时才落库）
  scriptForm.id = null
  scriptForm.name = ''
  scriptForm.lang = 'javascript'
  scriptForm.content = ''
  scriptForm.description = ''
  scriptForm.version = 1
  isDraft.value = true
  scriptGuard.markSaved()
}

async function doSaveScript() {
  if (isDraft.value) {
    // 草稿态首次保存：落库后干净地切到已保存脚本（selectScript 会重置表单 + isDraft=false + markSaved）
    const created = await apifoxApi.createScript(props.projectId, {
      name: scriptForm.name.trim(),
      lang: scriptForm.lang,
      content: scriptForm.content,
      description: scriptForm.description || null,
    })
    await loadScripts()
    await selectScript(created.id)
    return
  }
  if (scriptForm.id == null) return
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
  if (!scriptForm.name.trim()) {
    ElMessage.warning('请先填写脚本名称')
    return false
  }
  saving.value = true
  try {
    await doSaveScript()
    scriptGuard.markSaved()
    ElMessage.success('已保存')
    return true
  } catch (e) {
    if (!isConflict(e)) return false // 非冲突错误已由 api 拦截器提示
    if (scriptForm.id == null) return false
    let resolved = false
    await resolveSaveConflict({
      reload: async () => {
        await selectScript(scriptForm.id!)
        resolved = true
      },
      overwrite: async () => {
        if (scriptForm.id == null) return
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

async function delScript(s: Schemas['ScriptBrief']) {
  await ElMessageBox.confirm(`确认删除脚本「${s.name}」？被用例引用时会被拦截。`, '提示', {
    type: 'warning',
  })
  await apifoxApi.deleteScript(s.id)
  if (scriptForm.id === s.id) {
    isDraft.value = false
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
  gap: var(--ax-space-4);
  flex: 1;
  min-width: 0;
}

/* list-panel / list-toolbar 见 apifox-workspace.css */
.item {
  display: flex;
  align-items: center;
  gap: var(--ax-space-1-5);
  padding: var(--ax-space-1-5) var(--ax-space-2);
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
  gap: var(--ax-space-2);
  margin-bottom: var(--ax-space-2);
}

.desc-input {
  margin-bottom: var(--ax-space-2);
}
</style>

<template>
  <div class="scripts-panel h-full">
    <div class="list-panel h-full">
      <div class="list-toolbar">
        <span>SQL 脚本</span>
        <el-button type="primary" size="small" @click="addScript">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div
        v-for="s in scripts"
        :key="s.id"
        class="item"
        :class="{ active: form.id === s.id }"
        @click="onSelect(s.id)"
      >
        <el-tag size="small" type="warning">SQL</el-tag>
        <span class="item-name">{{ s.name }}</span>
        <el-button link type="danger" size="small" @click.stop="del(s)">删</el-button>
      </div>
      <el-empty v-if="scripts.length === 0" description="暂无 SQL 脚本" :image-size="60" />
    </div>

    <div class="editor-panel h-full flex flex-col">
      <div
        v-if="isDraft || form.id"
        :key="form.id ?? 'draft'"
        class="editor-body flex flex-1 flex-col min-h-0"
      >
        <div class="row1">
          <el-input
            v-model="form.name"
            placeholder="SQL 脚本名称（保存前填写）"
            :maxlength="TITLE_MAX_LEN"
            style="width: 240px"
          />
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button @click="debugVisible = true">调试</el-button>
          <el-tag v-if="isDraft" size="small" type="info">未保存草稿</el-tag>
        </div>
        <el-input
          v-model="form.description"
          placeholder="描述（选填）"
          :maxlength="DESC_MAX_LEN"
          show-word-limit
          class="desc-input"
        />
        <CodeEditor v-model="form.content" language="sql" height="" class="flex-1" />
      </div>
      <el-empty
        v-else
        description="选择或新建一个 SQL 脚本（跟随项目，可被前后置「数据库脚本」引用）"
      />
    </div>

    <SqlScriptDebugDialog v-model:visible="debugVisible" :content="form.content" />
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
import SqlScriptDebugDialog from '@/components/apifox/script/SqlScriptDebugDialog.vue'

const props = defineProps<{ projectId: Id }>()

const scripts = ref<Schemas['SqlScriptBrief'][]>([])
const saving = ref(false)
const debugVisible = ref(false)
const isDraft = ref(false)
const form = reactive({
  id: null as number | null,
  name: '',
  content: '',
  description: '',
  version: 1,
})

async function loadScripts() {
  scripts.value = await apifoxApi.listSqlScripts(props.projectId)
}

const guard = useUnsavedGuard({
  serialize: () =>
    JSON.stringify({
      id: form.id,
      name: form.name,
      content: form.content,
      description: form.description,
    }),
  save: () => save(),
  name: () => form.name,
})

async function select(sid: Id) {
  const s = await apifoxApi.getSqlScript(sid)
  isDraft.value = false
  form.id = s.id
  form.name = s.name
  form.content = s.content
  form.description = s.description || ''
  form.version = s.version ?? 1
  guard.markSaved()
}

async function onSelect(id: number) {
  if (id === form.id) return
  if (!(await guard.confirmLeave())) return
  await select(id)
}

async function addScript() {
  if (!(await guard.confirmLeave())) return
  form.id = null
  form.name = ''
  form.content = ''
  form.description = ''
  form.version = 1
  isDraft.value = true
  guard.markSaved()
}

async function doSave() {
  if (isDraft.value) {
    const created = await apifoxApi.createSqlScript(props.projectId, {
      name: form.name.trim(),
      content: form.content,
      description: form.description || null,
    })
    await loadScripts()
    await select(created.id)
    return
  }
  if (form.id == null) return
  const updated = await apifoxApi.updateSqlScript(form.id, {
    name: form.name,
    content: form.content,
    description: form.description || null,
    expected_version: form.version,
  })
  form.version = updated.version
  await loadScripts()
}

async function save() {
  if (!form.name.trim()) {
    ElMessage.warning('请先填写 SQL 脚本名称')
    return false
  }
  if (!form.content.trim()) {
    ElMessage.warning('SQL 内容不能为空')
    return false
  }
  saving.value = true
  try {
    await doSave()
    guard.markSaved()
    ElMessage.success('已保存')
    return true
  } catch (e) {
    if (!isConflict(e)) return false
    if (form.id == null) return false
    let resolved = false
    await resolveSaveConflict({
      reload: async () => {
        await select(form.id!)
        resolved = true
      },
      overwrite: async () => {
        if (form.id == null) return
        const latest = await apifoxApi.getSqlScript(form.id)
        form.version = latest.version
        await doSave()
        guard.markSaved()
        resolved = true
      },
    })
    return resolved
  } finally {
    saving.value = false
  }
}

async function del(s: Schemas['SqlScriptBrief']) {
  await ElMessageBox.confirm(`确认删除 SQL 脚本「${s.name}」？被引用时会被拦截。`, '提示', {
    type: 'warning',
  })
  await apifoxApi.deleteSqlScript(s.id)
  if (form.id === s.id) {
    isDraft.value = false
    form.id = null
    form.name = ''
    form.content = ''
    form.description = ''
    form.version = 1
    guard.markSaved()
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

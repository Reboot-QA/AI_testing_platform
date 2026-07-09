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
          @click="selectScript(s.id)"
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

    <!-- 全局参数 -->
    <div v-else class="editor-panel">
      <div class="var-title">全局参数（项目级，执行时自动附加到请求 · P4 接入）</div>
      <el-table :data="params" size="small" border>
        <el-table-column label="位置" width="120">
          <template #default="{ row }">
            <el-select v-model="row.location" size="small" @change="updateParam(row)">
              <el-option v-for="l in LOCATIONS" :key="l" :label="l" :value="l" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="参数名" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.key" size="small" @change="updateParam(row)" />
          </template>
        </el-table-column>
        <el-table-column label="值" min-width="180">
          <template #default="{ row }">
            <el-input v-model="row.value" size="small" @change="updateParam(row)" />
          </template>
        </el-table-column>
        <el-table-column label="启用" width="70" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" size="small" @change="updateParam(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="delParam(row)">删</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="add-row">
        <el-select v-model="newParam.location" size="small" style="width: 110px">
          <el-option v-for="l in LOCATIONS" :key="l" :label="l" :value="l" />
        </el-select>
        <el-input v-model="newParam.key" size="small" placeholder="参数名" style="width: 160px" />
        <el-input v-model="newParam.value" size="small" placeholder="值" style="width: 200px" />
        <el-button size="small" type="primary" :disabled="!newParam.key.trim()" @click="addParam">
          + 新增参数
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const SECTIONS = [
  { key: 'scripts', label: '脚本库', icon: 'Tickets' },
  { key: 'params', label: '全局参数', icon: 'SetUp' },
]
const LOCATIONS = ['header', 'query', 'cookie', 'body']

const section = ref('scripts')
const scripts = ref([])
const params = ref([])
const saving = ref(false)
const scriptForm = reactive({ id: null, name: '', lang: 'javascript', content: '', description: '' })
const newParam = reactive({ location: 'header', key: '', value: '' })

async function loadScripts() {
  scripts.value = await apifoxApi.listScripts(pid.value)
}

async function loadParams() {
  params.value = await apifoxApi.listGlobalParams(pid.value)
}

async function selectScript(sid) {
  const s = await apifoxApi.getScript(sid)
  scriptForm.id = s.id
  scriptForm.name = s.name
  scriptForm.lang = s.lang
  scriptForm.content = s.content
  scriptForm.description = s.description || ''
}

async function addScript() {
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
    ElMessage.success('已保存')
    await loadScripts()
  } finally {
    saving.value = false
  }
}

async function delScript(s) {
  await ElMessageBox.confirm(`确认删除脚本「${s.name}」？被用例引用时会被拦截。`, '提示', { type: 'warning' })
  await apifoxApi.deleteScript(s.id)
  if (scriptForm.id === s.id) scriptForm.id = null
  ElMessage.success('已删除')
  await loadScripts()
}

async function addParam() {
  await apifoxApi.createGlobalParam(pid.value, {
    location: newParam.location,
    key: newParam.key.trim(),
    value: newParam.value,
  })
  newParam.key = ''
  newParam.value = ''
  await loadParams()
}

async function updateParam(row) {
  await apifoxApi.updateGlobalParam(row.id, {
    location: row.location,
    key: row.key,
    value: row.value,
    enabled: row.enabled,
  })
  await loadParams()
}

async function delParam(row) {
  await apifoxApi.deleteGlobalParam(row.id)
  await loadParams()
}

onMounted(async () => {
  await loadScripts()
  await loadParams()
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

.var-title {
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 12px;
}

.add-row {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>

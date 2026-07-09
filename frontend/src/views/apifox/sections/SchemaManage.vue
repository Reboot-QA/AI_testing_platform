<template>
  <div class="schema-manage">
    <div class="list-panel">
      <div class="list-toolbar">
        <span>数据模型</span>
        <el-button size="small" type="primary" @click="addSchema">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>
      <div
        v-for="s in schemas"
        :key="s.id"
        class="schema-item"
        :class="{ active: form.id === s.id }"
        @click="selectSchema(s.id)"
      >
        <el-icon><Document /></el-icon>
        <span class="schema-name">{{ s.name }}</span>
        <el-button link type="danger" size="small" @click.stop="delSchema(s)">删</el-button>
      </div>
      <el-empty v-if="schemas.length === 0" description="暂无数据模型" :image-size="60" />
    </div>

    <div class="editor-panel">
      <template v-if="form.id">
        <div class="row1">
          <el-input v-model="form.name" placeholder="模型名称" style="width: 260px" />
          <el-button @click="formatJson">格式化</el-button>
          <el-button type="primary" :loading="saving" @click="saveSchema">保存</el-button>
        </div>
        <el-input
          v-model="form.description"
          placeholder="描述（选填）"
          class="desc-input"
        />
        <el-input
          v-model="form.json_schema"
          type="textarea"
          :rows="22"
          class="json-input"
          placeholder='JSON Schema，例如 {"type":"object","properties":{"id":{"type":"integer"}}}'
        />
      </template>
      <el-empty v-else description="选择或新建一个数据模型开始编辑" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const schemas = ref([])
const saving = ref(false)
const form = reactive({ id: null, name: '', description: '', json_schema: '{}' })

async function loadSchemas() {
  schemas.value = await apifoxApi.listSchemas(pid.value)
}

async function selectSchema(sid) {
  const s = await apifoxApi.getSchema(sid)
  form.id = s.id
  form.name = s.name
  form.description = s.description || ''
  form.json_schema = s.json_schema
}

async function addSchema() {
  const { value } = await ElMessageBox.prompt('模型名称', '新建数据模型', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  const created = await apifoxApi.createSchema(pid.value, { name: value, json_schema: '{}' })
  ElMessage.success('已创建')
  await loadSchemas()
  await selectSchema(created.id)
}

async function delSchema(s) {
  await ElMessageBox.confirm(`确认删除数据模型「${s.name}」？`, '提示', { type: 'warning' })
  await apifoxApi.deleteSchema(s.id)
  if (form.id === s.id) form.id = null
  ElMessage.success('已删除')
  await loadSchemas()
}

function formatJson() {
  try {
    form.json_schema = JSON.stringify(JSON.parse(form.json_schema), null, 2)
  } catch {
    ElMessage.error('JSON 格式不正确，无法格式化')
  }
}

async function saveSchema() {
  try {
    JSON.parse(form.json_schema)
  } catch {
    ElMessage.error('JSON 格式不正确，请修正后保存')
    return
  }
  saving.value = true
  try {
    await apifoxApi.updateSchema(form.id, {
      name: form.name,
      description: form.description || null,
      json_schema: form.json_schema,
    })
    ElMessage.success('已保存')
    await loadSchemas()
  } finally {
    saving.value = false
  }
}

onMounted(loadSchemas)
</script>

<style scoped>
.schema-manage {
  display: flex;
  gap: 16px;
  height: calc(100vh - 220px);
}

.list-panel {
  width: 260px;
  border-right: 1px solid #e2e8f0;
  overflow: auto;
  padding-right: 8px;
}

.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: #1a365d;
  margin-bottom: 8px;
}

.schema-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.schema-item:hover {
  background: #f1f5f9;
}

.schema-item.active {
  background: #e0ecff;
}

.schema-name {
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

.json-input :deep(textarea) {
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
}
</style>

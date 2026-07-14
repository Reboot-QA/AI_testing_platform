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
        <el-tag v-if="s.ref_count" size="small" type="info" title="被引用数（接口契约 + 模型 $ref）">
          {{ s.ref_count }}
        </el-tag>
        <el-button link type="danger" size="small" @click.stop="delSchema(s)">删</el-button>
      </div>
      <el-empty v-if="schemas.length === 0" description="暂无数据模型" :image-size="60" />
    </div>

    <div class="editor-panel">
      <template v-if="form.id">
        <div class="row1">
          <el-input v-model="form.name" placeholder="模型名称" style="width: 220px" />
          <el-tag v-if="currentRefCount" size="small" type="warning" title="被引用，改名会被后端拦截">
            被 {{ currentRefCount }} 处引用
          </el-tag>
          <el-radio-group v-model="viewMode" size="small" @change="onViewChange">
            <el-radio-button value="visual">可视化</el-radio-button>
            <el-radio-button value="source">源码</el-radio-button>
          </el-radio-group>
          <el-button type="primary" :loading="saving" @click="saveSchema">保存</el-button>
        </div>
        <el-input
          v-model="form.description"
          placeholder="描述（选填）"
          class="desc-input"
        />
        <div v-if="viewMode === 'visual'" class="schema-fields">
          <div class="sf-head">
            <span class="h-name">字段名</span>
            <span class="h-type">类型</span>
            <span class="h-req">必填</span>
            <span class="h-desc">说明</span>
          </div>
          <SchemaFieldRow
            v-for="(f, i) in fields"
            :key="f.uid"
            :field="f"
            :list="fields"
            :index="i"
            :models="refModels"
          />
          <el-button link type="primary" size="small" class="add-field" @click="addRootField">
            + 添加字段
          </el-button>
        </div>
        <CodeEditor v-else v-model="form.json_schema" language="json" height="440px" />
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
import { isConflict, resolveSaveConflict } from '@/composables/useSaveConflict'
import { fieldsToSchema, newField, schemaToFields } from '@/composables/useJsonSchema'
import CodeEditor from '@/components/apifox/common/CodeEditor.vue'
import SchemaFieldRow from '@/components/apifox/SchemaFieldRow.vue'

const route = useRoute()
const pid = computed(() => route.params.projectId)

const schemas = ref([])
const saving = ref(false)
const viewMode = ref('visual')
const fields = ref([])
const form = reactive({ id: null, name: '', description: '', json_schema: '{}', version: 1 })

// 可被引用的模型：排除当前模型自身（禁自引用）
const refModels = computed(() => schemas.value.filter((s) => s.id !== form.id))
// 当前模型被引用数（接口契约 + 其他模型 $ref），改名/删除保护提示
const currentRefCount = computed(() => schemas.value.find((s) => s.id === form.id)?.ref_count || 0)

function loadFieldsFromSource() {
  try {
    fields.value = schemaToFields(JSON.parse(form.json_schema || '{}'))
    return true
  } catch {
    return false
  }
}

async function loadSchemas() {
  schemas.value = await apifoxApi.listSchemas(pid.value)
}

async function selectSchema(sid) {
  const s = await apifoxApi.getSchema(sid)
  form.id = s.id
  form.name = s.name
  form.description = s.description || ''
  form.json_schema = s.json_schema
  form.version = s.version ?? 1
  viewMode.value = 'visual'
  loadFieldsFromSource()
}

function syncSourceFromFields() {
  form.json_schema = JSON.stringify(fieldsToSchema(fields.value), null, 2)
}

function onViewChange(mode) {
  if (mode === 'source') {
    syncSourceFromFields()
  } else if (!loadFieldsFromSource()) {
    ElMessage.error('源码 JSON 格式有误，请修正后再切换到可视化')
    viewMode.value = 'source'
  }
}

function addRootField() {
  fields.value.push(newField('string'))
}

async function addSchema() {
  const { value } = await ElMessageBox.prompt('模型名称', '新建数据模型', {
    inputPattern: /\S/,
    inputErrorMessage: '不能为空',
  })
  const created = await apifoxApi.createSchema(pid.value, {
    name: value,
    json_schema: '{"type":"object","properties":{}}',
  })
  ElMessage.success('已创建')
  await loadSchemas()
  await selectSchema(created.id)
}

async function delSchema(s) {
  const warn = s.ref_count
    ? `「${s.name}」被 ${s.ref_count} 处引用（接口契约/其他模型）。需先解除引用才能删除。`
    : `确认删除数据模型「${s.name}」？`
  await ElMessageBox.confirm(warn, '提示', { type: 'warning' })
  try {
    await apifoxApi.deleteSchema(s.id)
  } catch {
    return // 后端拦截(400)已由 api 拦截器提示具体原因，不再显示"已删除"
  }
  if (form.id === s.id) form.id = null
  ElMessage.success('已删除')
  await loadSchemas()
}

async function saveSchema() {
  if (viewMode.value === 'visual') {
    syncSourceFromFields()
  }
  try {
    JSON.parse(form.json_schema)
  } catch {
    ElMessage.error('JSON 格式不正确，请修正后保存')
    return
  }
  saving.value = true
  try {
    await doSaveSchema()
    ElMessage.success('已保存')
  } catch (e) {
    if (!isConflict(e)) return // 非冲突错误已由 api 拦截器提示
    await resolveSaveConflict({
      reload: async () => {
        await selectSchema(form.id)
      },
      overwrite: async () => {
        const latest = await apifoxApi.getSchema(form.id)
        form.version = latest.version
        await doSaveSchema()
      },
    })
  } finally {
    saving.value = false
  }
}

async function doSaveSchema() {
  const updated = await apifoxApi.updateSchema(form.id, {
    name: form.name,
    description: form.description || null,
    json_schema: form.json_schema,
    expected_version: form.version,
  })
  form.version = updated.version
  await loadSchemas()
}

onMounted(async () => {
  await loadSchemas()
  // 从接口树点数据模型跳转时自动选中
  const sid = Number(route.query.schema)
  if (sid && schemas.value.some((s) => s.id === sid)) await selectSchema(sid)
})
</script>

<style scoped>
.schema-manage {
  display: flex;
  gap: 16px;
  height: calc(100vh - 220px);
}

.list-panel {
  width: 260px;
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

.schema-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.schema-item:hover {
  background: var(--ax-bg-hover);
}

.schema-item.active {
  background: var(--ax-bg-active);
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

.schema-fields {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  padding: 10px 12px;
}

.sf-head {
  display: flex;
  gap: 8px;
  padding-bottom: 6px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--ax-border);
  font-size: 12px;
  color: var(--ax-text-secondary);
}

.sf-head .h-name {
  width: 180px;
}

.sf-head .h-type {
  width: 110px;
}

.sf-head .h-req {
  width: 52px;
}

.add-field {
  margin-top: 8px;
}
</style>

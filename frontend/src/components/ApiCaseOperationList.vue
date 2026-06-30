<template>
  <div class="operation-workspace-wrap">
    <div class="operation-workspace" :class="{ 'is-empty': !operations.length }">
      <div v-if="!operations.length" class="main-empty">
        <el-dropdown trigger="click" class="add-dropdown" @command="addOperation">
          <div class="add-operation-btn is-empty-state">
            <el-icon><Plus /></el-icon>
            <span>添加操作项</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="item in options"
                :key="item.type"
                :command="item.type"
                :disabled="!canAdd(item.type)"
              >
                <span class="dropdown-option">
                  <i class="option-icon" :style="{ background: item.color }" />
                  {{ item.label }}
                </span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <template v-else>
        <div class="operation-stack">
          <div
            v-for="(operation, index) in operations"
            :key="operation.id"
            class="operation-block"
            :class="{ 'is-disabled': operation.enabled === false }"
            @dragover.prevent
            @drop="onDrop(index)"
          >
            <div class="operation-block-head">
              <span
                class="drag-handle"
                title="拖动排序"
                draggable="true"
                @dragstart="onDragStart(index)"
              >
                <i class="drag-dots" />
              </span>
              <el-switch v-model="operation.enabled" size="small" />
              <span
                class="operation-type-tag"
                :style="{ '--tag-color': typeMeta(operation.type).color }"
              >
                {{ typeMeta(operation.type).label }}
              </span>
              <div v-if="operation.type === 'wait'" class="wait-inline">
                <el-input-number
                  v-model="operation.ms"
                  :min="1"
                  :max="3600000"
                  size="small"
                  controls-position="right"
                />
                <span class="inline-unit">ms</span>
              </div>
              <el-button link type="danger" class="block-delete" @click="removeOperation(index)">
                删除
              </el-button>
            </div>

            <div class="operation-block-body">
              <div v-if="typeMeta(operation.type).description" class="type-description">
                {{ typeMeta(operation.type).description }}
              </div>

              <template v-if="operation.type === 'script'">
                <div class="script-toolbar">
                  <span class="inline-label">脚本语言</span>
                  <el-radio-group v-model="operation.lang" size="small">
                    <el-radio-button value="javascript">JavaScript</el-radio-button>
                    <el-radio-button value="python">Python</el-radio-button>
                  </el-radio-group>
                  <el-button
                    size="small"
                    type="success"
                    :loading="debugLoading && debuggingId === operation.id"
                    :disabled="!activeScript(operation)?.trim()"
                    @click="$emit('debug-script', operation)"
                  >
                    调试运行
                  </el-button>
                </div>
                <el-input
                  :model-value="activeScript(operation)"
                  type="textarea"
                  :rows="10"
                  class="script-editor"
                  placeholder=""
                  @update:model-value="(value) => updateScript(operation, value)"
                />
                <div class="script-hints">
                  <div class="form-tip">示例脚本：</div>
                  <pre class="script-hint-pre">{{ scriptSample(operation.lang, phase) }}</pre>
                  <div class="form-tip">{{ scriptUsageTip(operation.lang, phase) }}</div>
                </div>
                <div
                  v-if="debugResult && debuggingId === operation.id"
                  class="pre-script-debug-result"
                >
                  <div class="pre-debug-toolbar">
                    <el-tag :type="debugResult.status === 'passed' ? 'success' : 'danger'" size="small">
                      {{ debugResult.status === 'passed' ? '调试成功' : '调试失败' }}
                    </el-tag>
                    <span v-if="debugResult.error_message" class="pre-debug-error">
                      {{ debugResult.error_message }}
                    </span>
                  </div>
                  <div v-if="debugResult.logs?.length" class="pre-debug-block">
                    <div class="block-label">运行日志</div>
                    <pre class="response-pre">{{ debugResult.logs.join('\n') }}</pre>
                  </div>
                  <div v-if="debugVariableRows.length" class="pre-debug-block">
                    <div class="block-label">变量结果</div>
                    <el-table :data="debugVariableRows" size="small" border>
                      <el-table-column prop="key" label="变量名" min-width="140" />
                      <el-table-column prop="value" label="值" min-width="220" show-overflow-tooltip />
                    </el-table>
                  </div>
                </div>
              </template>

              <template v-else-if="operation.type === 'database'">
                <el-form label-width="88px" size="small" class="database-form">
                  <el-row :gutter="12">
                    <el-col :span="8">
                      <el-form-item label="类型">
                        <el-select v-model="operation.db.driver" style="width: 100%">
                          <el-option label="MySQL" value="mysql" />
                          <el-option label="PostgreSQL" value="postgresql" />
                        </el-select>
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="主机">
                        <el-input v-model="operation.db.host" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="端口">
                        <el-input-number
                          v-model="operation.db.port"
                          :min="1"
                          :max="65535"
                          style="width: 100%"
                        />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <el-row :gutter="12">
                    <el-col :span="8">
                      <el-form-item label="数据库">
                        <el-input v-model="operation.db.database" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="用户名">
                        <el-input v-model="operation.db.username" />
                      </el-form-item>
                    </el-col>
                    <el-col :span="8">
                      <el-form-item label="密码">
                        <el-input v-model="operation.db.password" type="password" show-password />
                      </el-form-item>
                    </el-col>
                  </el-row>
                  <el-form-item label="SQL">
                    <el-input
                      v-model="operation.db.sql"
                      type="textarea"
                      :rows="4"
                      placeholder="SELECT id FROM users LIMIT 1"
                    />
                  </el-form-item>
                </el-form>
              </template>

              <template v-else-if="operation.type === 'assertion'">
                <el-input v-model="operation.content" type="textarea" :rows="6" class="script-editor" />
                <div class="form-tip">支持 status_code、json_path、contains、header、response_time</div>
              </template>

              <template v-else-if="operation.type === 'extract'">
                <ApiResponseExtractTable v-model:rows="operation.rows" :response-body="responseBody" />
                <div class="form-tip">响应体使用 JSON Path（如 $.code、$.data.token）；响应头填写 Header 名称</div>
              </template>
            </div>
          </div>
        </div>

        <el-dropdown trigger="click" class="bottom-add-dropdown" @command="addOperation">
          <div class="add-operation-btn is-compact">
            <el-icon><Plus /></el-icon>
            <span>添加操作项</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="item in options"
                :key="item.type"
                :command="item.type"
                :disabled="!canAdd(item.type)"
              >
                <span class="dropdown-option">
                  <i class="option-icon" :style="{ background: item.color }" />
                  {{ item.label }}
                </span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </div>

    <div v-if="$slots.footer" class="operation-footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import ApiResponseExtractTable from '@/components/ApiResponseExtractTable.vue'
import {
  PRE_OPERATION_OPTIONS,
  POST_OPERATION_OPTIONS,
  activePreScript,
  canAddOperation,
  createOperation,
} from '@/utils/apiCaseConfig'

const props = defineProps({
  operations: { type: Array, default: () => [] },
  phase: { type: String, required: true },
  responseBody: { type: String, default: '' },
  debugResult: { type: Object, default: null },
  debuggingId: { type: String, default: '' },
  debugLoading: { type: Boolean, default: false },
  debugVariableRows: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:operations', 'debug-script'])

const dragIndex = ref(null)

const options = computed(() =>
  props.phase === 'pre' ? PRE_OPERATION_OPTIONS : POST_OPERATION_OPTIONS
)

function typeMeta(type) {
  return options.value.find((item) => item.type === type) || { label: type, color: '#909399', description: '' }
}

function canAdd(type) {
  return canAddOperation(props.operations, type, props.phase)
}

function addOperation(type) {
  if (!canAdd(type)) return
  const operation = createOperation(type)
  if (operation.type === 'extract') {
    operation.expanded = true
  }
  emitUpdate([...props.operations, operation])
}

function removeOperation(index) {
  emitUpdate(props.operations.filter((_, idx) => idx !== index))
}

function emitUpdate(next) {
  emit('update:operations', next)
}

function activeScript(operation) {
  return activePreScript(operation.stores, operation.lang)
}

function updateScript(operation, value) {
  const key = operation.lang === 'python' ? 'python' : 'javascript'
  operation.stores[key] = value
}

function scriptSample(lang, phase) {
  if (phase === 'post') {
    return lang === 'python'
      ? "import json\n# 读取响应并写入 variables\n# body = json.loads(response_body) if response_body else {}\n# variables['token'] = body.get('data', {}).get('token', '')"
      : "// 读取响应并写入 variables\n// variables.token = response?.data?.token || ''"
  }
  return lang === 'python'
    ? "from faker import Faker\nfake = Faker('zh_CN')\nvariables['phone'] = fake.phone_number()"
    : "variables.phone = String(Date.now())"
}

function scriptUsageTip(lang, phase) {
  if (phase === 'post') {
    return lang === 'python'
      ? '后置脚本：从 response_body / response_headers 读取响应，写入 variables 后供套件后续用例引用'
      : '后置脚本：从 response 对象读取响应，写入 variables 后供套件后续用例引用'
  }
  return lang === 'python'
    ? 'Python：写入 variables 后，在 Header / Body 中用 {{变量名}} 引用；字符串需加引号'
    : 'JavaScript：写入 variables 后，在 Header / Body 中用 {{变量名}} 引用'
}

function onDragStart(index) {
  dragIndex.value = index
}

function onDrop(index) {
  if (dragIndex.value == null || dragIndex.value === index) return
  const next = [...props.operations]
  const [item] = next.splice(dragIndex.value, 1)
  next.splice(index, 0, item)
  dragIndex.value = null
  emitUpdate(next)
}
</script>

<style scoped>
.operation-workspace-wrap {
  width: 100%;
}

.operation-workspace {
  min-height: 360px;
  border: 1px solid #ebeef5;
  border-radius: 2px;
  background: #fff;
}

.main-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 360px;
  padding: 24px;
  box-sizing: border-box;
}

.add-dropdown {
  display: block;
  width: 100%;
}

.main-empty .add-operation-btn.is-empty-state {
  width: 100%;
  min-height: 280px;
}

.operation-stack {
  padding: 12px 12px 0;
}

.operation-block {
  margin-bottom: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fff;
  overflow: hidden;
}

.operation-block.is-disabled {
  opacity: 0.72;
}

.operation-block-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
}

.drag-handle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  cursor: grab;
  color: #c0c4cc;
  flex-shrink: 0;
}

.drag-dots {
  display: block;
  width: 10px;
  height: 14px;
  background:
    radial-gradient(circle, #c0c4cc 1.5px, transparent 1.6px) 0 0 / 10px 7px repeat;
}

.operation-type-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--tag-color);
  background: color-mix(in srgb, var(--tag-color) 12%, white);
  border: 1px solid color-mix(in srgb, var(--tag-color) 28%, white);
}

.wait-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}

.inline-unit {
  font-size: 12px;
  color: #909399;
}

.block-delete {
  margin-left: auto;
}

.operation-block-body {
  padding: 12px 16px 16px;
}

.script-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.inline-label {
  font-size: 13px;
  color: #606266;
}

.script-editor {
  font-family: Consolas, Monaco, monospace;
}

.script-hints {
  margin-top: 8px;
  user-select: text;
}

.script-hint-pre {
  margin: 4px 0 8px;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  color: #606266;
  user-select: text;
  cursor: text;
}

.form-tip {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
  user-select: text;
}

.type-description {
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.6;
  color: #606266;
  user-select: text;
  cursor: text;
}

.database-form {
  max-width: 960px;
}

.pre-script-debug-result {
  margin-top: 12px;
  padding: 12px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.pre-debug-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.pre-debug-error {
  font-size: 12px;
  color: #f56c6c;
}

.pre-debug-block {
  margin-top: 10px;
}

.block-label {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}

.response-pre {
  margin: 0;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}

.bottom-add-dropdown {
  display: block;
  padding: 0 12px 12px;
}

.add-operation-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 100%;
  border: 1px dashed #dcdfe6;
  border-radius: 2px;
  background: #fff;
  color: #909399;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  box-sizing: border-box;
  transition: color 0.2s, border-color 0.2s, background-color 0.2s;
  user-select: none;
}

.add-operation-btn.is-compact {
  height: 42px;
}

.add-operation-btn.is-empty-state {
  background: #fafbfc;
}

.add-operation-btn:hover {
  color: #606266;
  border-color: #c0c4cc;
  background: #f5f7fa;
}

.operation-footer {
  padding: 12px 0 0;
  width: 100%;
}

.dropdown-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.option-icon {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
}
</style>

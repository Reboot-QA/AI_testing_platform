<template>
  <el-dialog
    :model-value="visible"
    :title="action === 'update' ? '更新 Swagger（增量同步）' : '导入 OpenAPI / Swagger'"
    width="620px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-radio-group v-model="action" size="small" class="mode-switch" @change="resetDiff">
      <el-radio-button value="import">首次导入</el-radio-button>
      <el-radio-button value="update">更新同步</el-radio-button>
    </el-radio-group>

    <template v-if="!diff">
      <el-radio-group v-model="mode" size="small" class="mode-switch">
        <el-radio-button value="url">URL 拉取</el-radio-button>
        <el-radio-button value="content">粘贴 JSON</el-radio-button>
      </el-radio-group>

      <el-input
        v-if="mode === 'url'"
        v-model="url"
        placeholder="如 http://127.0.0.1:8000/openapi.json（本平台自身接口）"
      />
      <el-input
        v-else
        v-model="content"
        type="textarea"
        :rows="12"
        placeholder="粘贴 OpenAPI 3.x JSON 文档"
      />
      <p class="tip">{{ tip }}</p>
    </template>

    <template v-else>
      <ImportDiffPreview :diff="diff" />
      <el-checkbox v-model="deleteUnreferenced" class="del-opt">
        同时删除「新 Swagger 已移除且无用例引用」的接口（连同其用例）
      </el-checkbox>
    </template>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>

      <el-button
        v-if="action === 'import'"
        type="primary"
        :loading="busy"
        :disabled="!canSubmit"
        @click="doImport"
      >
        导入
      </el-button>

      <template v-else-if="!diff">
        <el-button type="primary" :loading="busy" :disabled="!canSubmit" @click="doPreview">
          预览变更
        </el-button>
      </template>

      <template v-else>
        <el-button @click="resetDiff">返回修改</el-button>
        <el-button type="primary" :loading="busy" @click="doApply">应用更新</el-button>
      </template>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import ImportDiffPreview from './ImportDiffPreview.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  projectId: { type: [String, Number], required: true },
  defaultAction: { type: String, default: 'import' }, // 'import' | 'update'：打开时初始模式
})
const emit = defineEmits(['update:visible', 'imported'])

const action = ref('import')
const mode = ref('url')
const url = ref('')
const content = ref('')
const busy = ref(false)
const diff = ref(null)
const deleteUnreferenced = ref(false)

const tip = computed(() =>
  action.value === 'update'
    ? '按「方法+路径」比对：新增接口会创建、变更接口只更新请求定义（用例不动）、移除接口先预览再决定。'
    : '按接口 tag 自动建文件夹归类；已存在的同「方法+路径」接口会跳过不覆盖。',
)

const canSubmit = computed(() =>
  mode.value === 'url' ? !!url.value.trim() : !!content.value.trim(),
)

const payload = () =>
  mode.value === 'url' ? { url: url.value.trim() } : { content: content.value }

// 按项目记住上次拉取地址（更新 Swagger 通常反复用同一个 openapi.json 地址）
const urlStoreKey = () => `apifox:lastImportUrl:${props.projectId}`
function rememberUrl() {
  if (mode.value === 'url' && url.value.trim()) {
    localStorage.setItem(urlStoreKey(), url.value.trim())
  }
}

function resetDiff() {
  diff.value = null
  deleteUnreferenced.value = false
}

// 打开时按调用方指定初始模式 + 回填上次地址；关闭时清空，避免下次打开残留预览/输入
watch(
  () => props.visible,
  (open) => {
    if (open) {
      action.value = props.defaultAction === 'update' ? 'update' : 'import'
      url.value = localStorage.getItem(urlStoreKey()) || ''
    } else {
      resetDiff()
      url.value = ''
      content.value = ''
    }
  },
)

async function doImport() {
  busy.value = true
  try {
    const report = await apifoxApi.importOpenapi(props.projectId, payload())
    rememberUrl()
    ElMessage.success(
      `导入完成：新建 ${report.created} 个接口、${report.schemas_created || 0} 个数据模型、` +
        `跳过 ${report.skipped} 个、新建文件夹 ${report.folders_created} 个`,
    )
    emit('update:visible', false)
    emit('imported')
  } finally {
    busy.value = false
  }
}

async function doPreview() {
  busy.value = true
  try {
    diff.value = await apifoxApi.importDiff(props.projectId, payload())
    rememberUrl()
  } finally {
    busy.value = false
  }
}

async function doApply() {
  busy.value = true
  try {
    const report = await apifoxApi.importSync(props.projectId, {
      ...payload(),
      delete_unreferenced: deleteUnreferenced.value,
    })
    ElMessage.success(
      `同步完成：新增 ${report.added}、更新 ${report.updated}、删除 ${report.deleted}、` +
        `保留(被引用) ${report.kept_referenced}、新增数据模型 ${report.schemas_created}`,
    )
    if (report.warnings.length) {
      await ElMessageBox.alert(report.warnings.join('\n'), '以下被引用接口未删除，请处理', {
        type: 'warning',
      })
    }
    emit('update:visible', false)
    emit('imported')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.mode-switch {
  margin-bottom: 12px;
}

.tip {
  color: var(--ax-text-placeholder);
  font-size: 12px;
  margin-top: 8px;
}

.del-opt {
  margin-top: 12px;
}
</style>

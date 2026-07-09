<template>
  <el-dialog
    :model-value="visible"
    title="导入 OpenAPI / Swagger"
    width="560px"
    @update:model-value="$emit('update:visible', $event)"
  >
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
    <p class="tip">按接口 tag 自动建文件夹归类；已存在的同「方法+路径」接口会跳过不覆盖。</p>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="importing" :disabled="!canSubmit" @click="doImport">
        导入
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apifoxApi } from '@/api'

const props = defineProps({
  visible: { type: Boolean, default: false },
  projectId: { type: [String, Number], required: true },
})
const emit = defineEmits(['update:visible', 'imported'])

const mode = ref('url')
const url = ref('')
const content = ref('')
const importing = ref(false)

const canSubmit = computed(() =>
  mode.value === 'url' ? !!url.value.trim() : !!content.value.trim()
)

async function doImport() {
  importing.value = true
  try {
    const payload = mode.value === 'url' ? { url: url.value.trim() } : { content: content.value }
    const report = await apifoxApi.importOpenapi(props.projectId, payload)
    ElMessage.success(
      `导入完成：新建 ${report.created} 个接口、跳过 ${report.skipped} 个、新建文件夹 ${report.folders_created} 个`
    )
    emit('update:visible', false)
    emit('imported')
  } finally {
    importing.value = false
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
</style>

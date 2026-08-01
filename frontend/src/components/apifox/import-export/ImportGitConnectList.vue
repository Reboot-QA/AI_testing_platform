<template>
  <div class="git-form">
    <p class="git-tip">
      粘贴 Git 仓库中数据文件的 <b>raw</b> 地址（如 <code>raw.githubusercontent.com/...</code> 或
      GitLab <code>/-/raw/...</code>）；私有仓库填 Personal Access Token。
    </p>
    <label class="git-req">Raw 文件 URL *</label>
    <el-input
      v-model="rawUrl"
      :maxlength="URL_MAX_LEN"
      placeholder="https://raw.githubusercontent.com/org/repo/main/openapi.json"
    />
    <label class="git-lbl">Personal Access Token（私有仓库）</label>
    <el-input
      v-model="token"
      :maxlength="SECRET_MAX_LEN"
      type="password"
      placeholder="ghp_xxx / glpat-xxx，公开仓库可留空"
      show-password
    />
    <div class="git-actions">
      <el-button type="primary" :loading="busy" :disabled="!rawUrl.trim()" @click="doImport">
        从 Git 导入
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { SECRET_MAX_LEN, URL_MAX_LEN } from '@/constants/limits'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apifoxApi } from '@/api'
import { useRouteParamId } from '@/composables/useRouteParamId'

const pid = useRouteParamId()
const rawUrl = ref('')
const token = ref('')
const busy = ref(false)

async function doImport() {
  busy.value = true
  try {
    const report = await apifoxApi.importOpenapi(pid.value, {
      url: rawUrl.value.trim(),
      git_token: token.value.trim() || undefined,
      on_conflict: 'skip', // Git 面板是直连导入，不走预览勾选：已存在的一律跳过
      with_schemas: true,
    })
    ElMessage.success(
      `导入完成：新建 ${report.created} 个接口、${report.schemas_created || 0} 个数据模型、跳过 ${report.skipped} 个`,
    )
    rawUrl.value = ''
    token.value = ''
  } catch {
    ElMessage.error('从 Git 导入失败，请检查地址与 Token')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.git-form {
  display: flex;
  flex-direction: column;
  gap: var(--ax-space-2);
}

.git-tip {
  margin: 0 0 var(--ax-space-1);
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text-secondary);
  line-height: var(--ax-leading-normal);
}

.git-tip code {
  padding: 0 var(--ax-space-1);
  background: var(--ax-bg-subtle);
  border-radius: var(--ax-radius-sm);
}

.git-req,
.git-lbl {
  font-size: var(--ax-text-body-sm-size);
  color: var(--ax-text);
}

.git-lbl {
  margin-top: var(--ax-space-2);
  color: var(--ax-text-secondary);
}

.git-actions {
  margin-top: var(--ax-space-3);
  display: flex;
  justify-content: flex-end;
}
</style>

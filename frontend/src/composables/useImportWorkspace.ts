/**
 * 导入页内工作台：文件/URL/粘贴导入 →「预览 & 配置」（勾选接口 + 选目标目录 + 已存在接口的处理）。
 * 项目已有接口不再强制走更新同步，只在预览里标出「已存在/有变更」，由用户自行决定；
 * 需要清理文档中已移除的接口时，再从预览面板切到「更新同步」。
 */

import { computed, onMounted, ref, watch, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { ImportDiffView, ImportSourceFormat } from '@/types/apifox'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useRouteParamId } from '@/composables/useRouteParamId'

export type ImportMode = 'file' | 'url' | 'git' | 'paste' | 'stub'

/** 「预览 & 配置」面板回传的导入选择 */
export interface ImportChoice {
  selectedKeys: string[]
  targetFolderId: number | null
  onConflict: 'skip' | 'overwrite'
  withSchemas: boolean
}

function normalizeDiff(raw: Schemas['ImportDiffOut']): ImportDiffView {
  return { ...raw, added: raw.added ?? [], changed: raw.changed ?? [], removed: raw.removed ?? [] }
}

export function useImportWorkspace(format: Ref<ImportSourceFormat>) {
  const pid = useRouteParamId()

  const url = ref('')
  const basicAuth = ref(false)
  const basicAuthUser = ref('')
  const basicAuthPwd = ref('')
  const fileContent = ref('')
  const curlText = ref('')
  const hasStubFile = ref(false)
  const busy = ref(false)
  const mode = ref<ImportMode>('file')

  // 上次导入 URL（后端记住）：URL 模式下回填，方便再次导入同一地址
  const lastImportUrl = ref('')
  // 项目是否已有接口（导入过）：决定是否给出「更新同步」这个可选入口
  const hasEndpoints = ref(false)
  const preview = ref<Schemas['ImportPreviewOut'] | null>(null)
  const diff = ref<ImportDiffView | null>(null)
  const deleteUnreferenced = ref(false)

  const showContinue = computed(() => mode.value !== 'git')
  const canContinue = computed(() => {
    if (mode.value === 'url') return !!url.value.trim()
    if (mode.value === 'file') return !!fileContent.value
    if (mode.value === 'paste') return !!curlText.value.trim()
    if (mode.value === 'stub') return hasStubFile.value
    return false
  })

  async function loadLastUrl() {
    try {
      const r = await apifoxApi.getImportSource(pid.value)
      lastImportUrl.value = (r.url || '').trim()
    } catch {
      /* 无记录或拉取失败，忽略 */
    }
  }
  async function loadHasEndpoints() {
    try {
      hasEndpoints.value = (await apifoxApi.listEndpoints(pid.value)).length > 0
    } catch {
      hasEndpoints.value = false
    }
  }
  onMounted(() => {
    loadLastUrl()
    loadHasEndpoints()
  })

  // 进入 URL 模式时，输入框为空则回填上次导入地址
  watch(mode, (m) => {
    if (m === 'url' && !url.value && lastImportUrl.value) url.value = lastImportUrl.value
  })

  watch(format, () => {
    url.value = ''
    basicAuth.value = false
    basicAuthUser.value = ''
    basicAuthPwd.value = ''
    fileContent.value = ''
    curlText.value = ''
    hasStubFile.value = false
    resetPreview()
  })

  function comingSoon() {
    ElMessage.info('敬请期待')
  }

  function readFile(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(String(reader.result ?? ''))
      reader.onerror = () => reject(reader.error)
      reader.readAsText(file)
    })
  }

  async function onFile(file: File) {
    try {
      fileContent.value = await readFile(file)
      hasStubFile.value = false
    } catch {
      ElMessage.error('读取文件失败')
    }
  }

  function onStubFile(_file: File) {
    hasStubFile.value = true
    fileContent.value = ''
  }

  function payload(): Schemas['ImportRequest'] {
    if (mode.value === 'url') {
      const p: Schemas['ImportRequest'] = { url: url.value.trim() }
      if (basicAuth.value && basicAuthUser.value) {
        p.basic_auth = { username: basicAuthUser.value, password: basicAuthPwd.value }
      }
      return p
    }
    if (mode.value === 'paste') return { content: curlText.value.trim() }
    return { content: fileContent.value }
  }

  function clearInputs() {
    fileContent.value = ''
    curlText.value = ''
    hasStubFile.value = false
  }

  /** 按用户在「预览 & 配置」里的勾选与位置执行导入 */
  async function confirmImport(choice: ImportChoice) {
    busy.value = true
    try {
      const report = await apifoxApi.importOpenapi(pid.value, {
        ...payload(),
        target_folder_id: choice.targetFolderId,
        selected_keys: choice.selectedKeys,
        on_conflict: choice.onConflict,
        with_schemas: choice.withSchemas,
      })
      ElMessage.success(
        `导入完成：新建 ${report.created} 个接口、更新 ${report.updated || 0} 个、` +
          `跳过 ${report.skipped} 个、新建文件夹 ${report.folders_created} 个、` +
          `数据模型 ${report.schemas_created || 0} 个`,
      )
      clearInputs()
      resetPreview()
      await loadLastUrl() // URL 导入后记住地址
      await loadHasEndpoints()
      return true
    } finally {
      busy.value = false
    }
  }

  /** 拉取「预览 & 配置」数据（只读，不写库） */
  async function loadPreview() {
    busy.value = true
    try {
      preview.value = await apifoxApi.importPreview(pid.value, payload())
    } finally {
      busy.value = false
    }
  }

  /** 可选入口：切到更新同步，看新增/变更/移除并可清理已移除接口 */
  async function loadDiff() {
    busy.value = true
    try {
      diff.value = normalizeDiff(await apifoxApi.importDiff(pid.value, payload()))
    } finally {
      busy.value = false
    }
  }

  async function applySync() {
    busy.value = true
    try {
      const changedCount = diff.value?.changed.length ?? 0
      const report = await apifoxApi.importSync(pid.value, {
        ...payload(),
        delete_unreferenced: deleteUnreferenced.value,
      })
      ElMessage.success(
        `同步完成：新增 ${report.added}、更新 ${report.updated}、删除 ${report.deleted}、` +
          `保留(被引用) ${report.kept_referenced}、新增数据模型 ${report.schemas_created}`,
      )
      if (report.warnings?.length) {
        await ElMessageBox.alert(report.warnings.join('\n'), '以下被引用接口未删除，请处理', {
          type: 'warning',
        })
      }
      // 变更接口若有用例会被后端标「待复核」，可到「AI 任务中心」为其生成用例
      if (changedCount) {
        ElMessage.info(`${changedCount} 个接口契约有变更，可到「AI 任务中心」为待复核接口生成用例`)
      }
      clearInputs()
      resetPreview()
      await loadHasEndpoints()
      return true
    } finally {
      busy.value = false
    }
  }

  /** 从更新同步退回「预览 & 配置」 */
  function backToPreview() {
    diff.value = null
    deleteUnreferenced.value = false
  }

  function resetPreview() {
    preview.value = null
    backToPreview()
  }

  /** 输入完成 → 进入「预览 & 配置」（不直接落库，由用户勾选后再导入） */
  async function onContinue() {
    if (mode.value === 'stub') {
      comingSoon()
      return
    }
    if (!canContinue.value) return
    await loadPreview()
  }

  return {
    url,
    basicAuth,
    basicAuthUser,
    basicAuthPwd,
    curlText,
    busy,
    mode,
    showContinue,
    canContinue,
    hasEndpoints,
    preview,
    diff,
    deleteUnreferenced,
    comingSoon,
    onFile,
    onStubFile,
    onContinue,
    confirmImport,
    loadDiff,
    applySync,
    backToPreview,
    resetPreview,
  }
}

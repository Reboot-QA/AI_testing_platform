import { ref, type Ref } from 'vue'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'

type ProjectScript = Schemas['ScriptBrief']

// 项目脚本库列表（用例/接口前后置脚本引用选择用）。多处复用，避免重复 loadScripts。
export function useProjectScripts(pid: Ref<number | string | null | undefined>) {
  const scripts = ref<ProjectScript[]>([])

  async function loadScripts(): Promise<void> {
    scripts.value = await apifoxApi.listScripts(pid.value!)
  }

  return { scripts, loadScripts }
}

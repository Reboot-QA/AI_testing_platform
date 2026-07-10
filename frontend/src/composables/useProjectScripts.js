import { ref } from 'vue'
import { apifoxApi } from '@/api'

// 项目脚本库列表（用例/接口前后置脚本引用选择用）。多处复用，避免重复 loadScripts。
export function useProjectScripts(pid) {
  const scripts = ref([])
  async function loadScripts() {
    scripts.value = await apifoxApi.listScripts(pid.value)
  }
  return { scripts, loadScripts }
}

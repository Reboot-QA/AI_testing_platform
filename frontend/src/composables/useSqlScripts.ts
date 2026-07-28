import { onMounted, ref } from 'vue'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useRouteParamId } from '@/composables/useRouteParamId'

/**
 * 加载项目级 SQL 脚本库，供前后置「数据库脚本」处理器选引用（SQL 脚本跟随项目，非环境级）。
 */
export function useSqlScripts() {
  const pid = useRouteParamId()
  const sqlScripts = ref<Schemas['SqlScriptBrief'][]>([])

  async function reloadSqlScripts() {
    sqlScripts.value = pid.value ? await apifoxApi.listSqlScripts(pid.value) : []
  }

  onMounted(reloadSqlScripts)

  return { sqlScripts, reloadSqlScripts }
}

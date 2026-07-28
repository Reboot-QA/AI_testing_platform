import { onMounted, onUnmounted, ref, watch } from 'vue'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'
import { useWorkspaceStore } from '@/stores/workspace'
import { useDatabaseManageDrawer } from '@/composables/useDatabaseManageDrawer'

/**
 * 按「当前选中环境」加载数据库连接，供前后置「数据库操作」处理器选连接。
 * 复用场景面板的加载 + watch 环境切换逻辑（数据库连接是环境级）。
 */
export function useEnvDatabases() {
  const store = useWorkspaceStore()
  const databases = ref<Schemas['DatabaseOut'][]>([])
  const { subscribeUpdated } = useDatabaseManageDrawer()

  async function reloadDatabases() {
    databases.value = store.currentEnvironmentId
      ? await apifoxApi.listDatabases(store.currentEnvironmentId)
      : []
  }

  onMounted(() => {
    void reloadDatabases()
    const unsub = subscribeUpdated(reloadDatabases)
    onUnmounted(unsub)
  })
  watch(() => store.currentEnvironmentId, reloadDatabases)

  return { databases, reloadDatabases }
}

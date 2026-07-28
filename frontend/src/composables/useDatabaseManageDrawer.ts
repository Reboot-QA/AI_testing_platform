import { ref } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'

const visible = ref(false)
const envId = ref<number | null>(null)
const openCreateOnShow = ref(false)

type Listener = () => void
const listeners = new Set<Listener>()

/** 接口调试/场景里打开「数据库连接管理」抽屉（按环境隔离） */
export function useDatabaseManageDrawer() {
  function open(environmentId?: number | null, opts?: { create?: boolean }) {
    const ws = useWorkspaceStore()
    envId.value = environmentId ?? ws.currentEnvironmentId
    openCreateOnShow.value = !!opts?.create
    visible.value = true
  }

  function close() {
    visible.value = false
  }

  function notifyUpdated() {
    listeners.forEach((fn) => fn())
  }

  function subscribeUpdated(fn: Listener): () => void {
    listeners.add(fn)
    return () => listeners.delete(fn)
  }

  return {
    visible,
    envId,
    openCreateOnShow,
    open,
    close,
    notifyUpdated,
    subscribeUpdated,
  }
}

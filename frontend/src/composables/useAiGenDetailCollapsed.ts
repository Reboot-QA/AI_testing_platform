import { computed, ref, watch, type Ref } from 'vue'
import { useUserStore } from '@/stores/user'

const STORAGE_PREFIX = 'apifox:ai-gen-detail-collapsed'

function storageKey(userId: number, endpointId: number): string {
  return `${STORAGE_PREFIX}:${userId}:${endpointId}`
}

function readCollapsed(userId: number, endpointId: number): boolean {
  if (!userId || !endpointId) return false
  try {
    return localStorage.getItem(storageKey(userId, endpointId)) === '1'
  } catch {
    return false
  }
}

function writeCollapsed(userId: number, endpointId: number, collapsed: boolean): void {
  if (!userId || !endpointId) return
  try {
    const key = storageKey(userId, endpointId)
    if (collapsed) localStorage.setItem(key, '1')
    else localStorage.removeItem(key)
  } catch {
    /* 隐私模式等写失败时忽略，仅影响本会话外的记忆 */
  }
}

/**
 * 单接口「AI 生成详情」收起记忆：按 用户 + 接口 持久化。
 * 手动收起后，下次进入默认不展开；本会话可临时展开，不影响记忆。
 */
export function useAiGenDetailCollapsed(endpointId: Ref<number>) {
  const userStore = useUserStore()
  const userId = computed(() => userStore.user?.id ?? 0)
  const preferCollapsed = ref(false)
  const sessionExpanded = ref(false)

  function syncFromStorage() {
    preferCollapsed.value = readCollapsed(userId.value, endpointId.value)
    sessionExpanded.value = false
  }

  watch([userId, endpointId], syncFromStorage, { immediate: true })

  function collapse() {
    preferCollapsed.value = true
    sessionExpanded.value = false
    writeCollapsed(userId.value, endpointId.value, true)
  }

  function expand() {
    sessionExpanded.value = true
  }

  return { preferCollapsed, sessionExpanded, collapse, expand }
}

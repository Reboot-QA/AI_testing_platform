import { onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { confirmUnsaved } from '@/composables/useSaveConflict'

export interface UnsavedGuardOptions {
  serialize: () => string
  save: () => Promise<boolean>
  name: () => string
}

// 单编辑区（选中即替换）的未保存保护：切换编辑对象 / 离开路由(切主 tab) / 关浏览器前，
// 若有未保存改动则提示「保存/不保存/取消」。用初始快照深比较判 dirty。
export function useUnsavedGuard({ serialize, save, name }: UnsavedGuardOptions) {
  const snapshot = ref(serialize())

  const isDirty = (): boolean => serialize() !== snapshot.value
  const markSaved = (): void => {
    snapshot.value = serialize()
  }

  async function confirmLeave(): Promise<boolean> {
    if (!isDirty()) return true
    const choice = await confirmUnsaved(name ? name() : '当前编辑')
    if (choice === 'cancel') return false
    if (choice === 'save') return !!(await save())
    return true
  }

  function beforeUnload(e: BeforeUnloadEvent): void {
    if (isDirty()) {
      e.preventDefault()
      e.returnValue = ''
    }
  }

  onMounted(() => window.addEventListener('beforeunload', beforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))
  onBeforeRouteLeave(() => confirmLeave())

  return { isDirty, markSaved, confirmLeave }
}

import { onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { confirmUnsaved } from '@/composables/useSaveConflict'

// 单编辑区（选中即替换）的未保存保护：切换编辑对象 / 离开路由(切主 tab) / 关浏览器前，
// 若有未保存改动则提示「保存/不保存/取消」。用初始快照深比较判 dirty。
//   serialize: () => string   当前编辑态序列化（快照比较用，须稳定）
//   save:      () => Promise<boolean>  保存，返回是否成功（保存失败/冲突未解则不放行）
//   name:      () => string   当前编辑对象名（弹窗展示）
export function useUnsavedGuard({ serialize, save, name }) {
  const snapshot = ref(serialize())

  const isDirty = () => serialize() !== snapshot.value
  // 加载新对象 / 保存成功后调用：把当前态记为「已保存基线」
  const markSaved = () => {
    snapshot.value = serialize()
  }

  // 返回 true=可离开，false=取消离开（保留编辑）
  async function confirmLeave() {
    if (!isDirty()) return true
    const choice = await confirmUnsaved(name ? name() : '当前编辑')
    if (choice === 'cancel') return false
    if (choice === 'save') return !!(await save())
    return true // discard：放弃改动，放行
  }

  function beforeUnload(e) {
    if (isDirty()) {
      e.preventDefault()
      e.returnValue = ''
    }
  }
  onMounted(() => window.addEventListener('beforeunload', beforeUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))
  // 切主 tab（路由离开）时守卫：单编辑区数据在组件内，销毁即丢
  onBeforeRouteLeave(() => confirmLeave())

  return { isDirty, markSaved, confirmLeave }
}

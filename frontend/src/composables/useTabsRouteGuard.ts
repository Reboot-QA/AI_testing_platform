import { onBeforeRouteLeave } from 'vue-router'
import { ElMessageBox } from 'element-plus'

// 多 tab 面板（接口管理/场景/套件）路由级未保存守卫：
// 切主 tab / 切项目 / 退出工作台等路由跳转时，若有未保存改动则确认，取消则阻止离开。
// （子页 v-if 切换不触发路由，故不影响 tab 数据在 Pinia 的持久留存。）
export function useTabsRouteGuard(hasAnyDirty: () => boolean): void {
  onBeforeRouteLeave(async () => {
    if (!hasAnyDirty()) return true
    try {
      await ElMessageBox.confirm('有未保存的改动，离开将丢弃这些改动。确定离开？', '未保存改动', {
        type: 'warning',
        confirmButtonText: '离开',
        cancelButtonText: '留下',
      })
      return true
    } catch {
      return false // 取消 → 阻止路由跳转
    }
  })
}

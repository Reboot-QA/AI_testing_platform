import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

// 多标签页会话同步：token 存在 localStorage，是所有标签页共用的。
// 在另一个标签页换账号登录后，本标签页仍持有上个用户的项目/环境/tab 等内存态，
// 却带着新账号的 token 去请求，就会连报「项目不存在」。故监听 token 变化即时对齐。
export function useSessionSync(): void {
  const userStore = useUserStore()
  const router = useRouter()

  function onStorage(e: StorageEvent): void {
    if (e.key !== 'token' || e.storageArea !== localStorage) return
    const next = e.newValue || ''
    if (next === userStore.token) return

    if (!next) {
      // 别的标签页登出了：本页同步清干净并回登录页
      if (!userStore.token) return
      userStore.logout(false)
      router.push('/login')
      return
    }
    // 别的标签页换了账号：内存态属于上个用户，整页重载最稳妥（重载后按新 token 重建）
    ElMessage.warning('检测到账号已切换，正在刷新页面')
    window.location.reload()
  }

  onMounted(() => window.addEventListener('storage', onStorage))
  onUnmounted(() => window.removeEventListener('storage', onStorage))
}

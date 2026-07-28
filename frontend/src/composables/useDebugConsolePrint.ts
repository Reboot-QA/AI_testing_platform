import { ref, watch } from 'vue'

const STORAGE_KEY = 'apifox_debug_console_print_db'

const enabled = ref(
  typeof localStorage !== 'undefined' && localStorage.getItem(STORAGE_KEY) === '1',
)

watch(enabled, (on) => {
  localStorage.setItem(STORAGE_KEY, on ? '1' : '0')
})

/** 调试发送：是否在控制台打印 SQL 查询结果（持久化到 localStorage） */
export function useDebugConsolePrint() {
  return { enabled }
}

import { type ComputedRef, onBeforeUnmount, ref, watch } from 'vue'
import type { Schemas } from '@/api/types'
import { apifoxApi } from '@/api'

/** 运行中自动打开报告抽屉并按 runId 轮询详情 */
export function useRunReportDrawer(options: {
  runId: ComputedRef<number | undefined>
  running: ComputedRef<boolean>
  eventsLength: ComputedRef<number>
}) {
  const drawerVisible = ref(false)
  const detail = ref<Schemas['RunOut'] | null>(null)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  async function refreshReport() {
    if (!options.runId.value) return
    try {
      detail.value = await apifoxApi.getRun(options.runId.value)
    } catch {
      /* 轮询单次失败忽略 */
    }
  }

  async function openReport() {
    if (!options.runId.value) return
    drawerVisible.value = true
    if (!detail.value || detail.value.id !== options.runId.value) {
      await refreshReport()
    }
  }

  function startPolling() {
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = setInterval(refreshReport, 1200)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function onDrawerClosed() {
    if (!options.running.value) stopPolling()
  }

  watch(options.runId, (rid, prev) => {
    if (!rid) return
    if (prev && prev !== rid) detail.value = null
    void openReport()
    if (options.running.value) startPolling()
  })

  watch(options.eventsLength, (len) => {
    if (len === 0) {
      drawerVisible.value = false
      detail.value = null
      stopPolling()
    }
  })

  watch(options.running, (active) => {
    if (active && options.runId.value) {
      startPolling()
    } else {
      stopPolling()
      if (options.runId.value) void refreshReport()
    }
  })

  onBeforeUnmount(stopPolling)

  return { drawerVisible, detail, refreshReport, onDrawerClosed }
}

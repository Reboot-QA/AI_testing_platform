import { inject, provide, ref, watch, type InjectionKey, type Ref } from 'vue'
import { apifoxApi } from '@/api'

// {{变量}} 可解析性：收集当前上下文能联动到的变量（环境变量 > 全局变量 > 全局参数）。
// 供 VarInput 高亮判定与 hover 提示；provide/inject 避免逐层传参。
interface ResolvedVar {
  value: string
  source: string
}
export type VarMap = Record<string, ResolvedVar>

const KEY: InjectionKey<Ref<VarMap>> = Symbol('resolvableVars')
const RELOAD_KEY: InjectionKey<() => Promise<void>> = Symbol('resolvableVarsReload')

export function provideResolvableVars(
  projectId: Ref<number | string>,
  currentEnvId: Ref<number | null>,
): Ref<VarMap> {
  const map = ref<VarMap>({})

  async function load() {
    const pid = Number(projectId.value)
    if (!pid) {
      map.value = {}
      return
    }
    const next: VarMap = {}
    try {
      // 优先级从低到高覆盖：全局参数 < 全局变量 < 当前环境变量
      const [params, globals] = await Promise.all([
        apifoxApi.listGlobalParams(pid),
        apifoxApi.listGlobalVars(pid),
      ])
      params.forEach((p) => {
        if (p.enabled && p.key) next[p.key] = { value: p.value ?? '', source: '全局参数' }
      })
      globals.forEach((g) => {
        if (g.enabled && g.key) next[g.key] = { value: g.effective_value ?? '', source: '全局变量' }
      })
      const eid = currentEnvId.value
      if (eid) {
        const envVars = await apifoxApi.listEnvVars(eid)
        envVars.forEach((v) => {
          if (v.enabled && v.key)
            next[v.key] = { value: v.effective_value ?? '', source: '环境变量' }
        })
      }
    } catch {
      // 全局拦截器已提示
    }
    map.value = next
  }

  watch([projectId, currentEnvId], load, { immediate: true })
  provide(KEY, map)
  provide(RELOAD_KEY, load)
  return map
}

export function useResolvableVars(): Ref<VarMap> {
  return inject(KEY, ref<VarMap>({}))
}

/** 环境/全局变量/参数写成功或提取落库后，刷新 {{变量}} 可解析集合 */
export function useResolvableVarsReload(): () => Promise<void> {
  return inject(RELOAD_KEY, async () => {})
}

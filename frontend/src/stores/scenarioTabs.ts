import { defineStore } from 'pinia'
import { apifoxApi } from '@/api'
import { normalizeSteps } from '@/utils/scenarioSteps'

export interface ScenarioForm {
  id: number
  name: string
  description: string
  priority: string
  steps: unknown[]
  run_config: { loop_count: number; dataset_id: number | null; propagate_auth: boolean }
}

export interface ScenarioTab {
  id: number
  name: string
  form: ScenarioForm
  snapshot: string
  version: number
  running: boolean
  runEvents: unknown[]
  saving: boolean
}

interface ProjectTabsState {
  tabs: ScenarioTab[]
  activeId: number | null
  lastActiveId: number | null
}

function scenarioToForm(s: any): ScenarioForm {
  return {
    id: s.id,
    name: s.name,
    description: s.description || '',
    priority: s.priority || 'medium',
    steps: normalizeSteps(s.steps || []),
    run_config: {
      loop_count: s.run_config?.loop_count ?? 1,
      dataset_id: s.run_config?.dataset_id ?? null,
      propagate_auth: s.run_config?.propagate_auth ?? true,
    },
  }
}

// 脏检测快照：只序列化会保存的字段（与旧 useUnsavedGuard 一致）
const snap = (f: ScenarioForm): string =>
  JSON.stringify({
    name: f.name,
    description: f.description,
    priority: f.priority,
    steps: f.steps,
    run_config: f.run_config,
  })

const _pending = new Set<string>()

function newTab(s: any): ScenarioTab {
  const form = scenarioToForm(s)
  return {
    id: s.id,
    name: s.name,
    form,
    snapshot: snap(form),
    version: s.version ?? 1,
    running: false,
    runEvents: [],
    saving: false,
  }
}

export const useScenarioTabsStore = defineStore('scenarioTabs', {
  state: () => ({ byProject: {} as Record<string, ProjectTabsState> }),
  getters: {
    tabsOf: (s) => (pid: number | string) => s.byProject[String(pid)]?.tabs || [],
    activeIdOf: (s) => (pid: number | string) => s.byProject[String(pid)]?.activeId ?? null,
  },
  actions: {
    _p(pid: number | string): ProjectTabsState {
      const k = String(pid)
      if (!this.byProject[k]) this.byProject[k] = { tabs: [], activeId: null, lastActiveId: null }
      return this.byProject[k]
    },
    findTab(pid: number | string, id: number | null): ScenarioTab | null {
      return this._p(pid).tabs.find((t) => t.id === id) || null
    },
    isDirty(tab: ScenarioTab | null): boolean {
      return !!tab && snap(tab.form) !== tab.snapshot
    },
    hasAnyDirty(pid: number | string): boolean {
      return this._p(pid).tabs.some((t) => this.isDirty(t))
    },
    activate(pid: number | string, id: number): void {
      const p = this._p(pid)
      if (p.activeId !== id) {
        p.lastActiveId = p.activeId
        p.activeId = id
      }
    },
    async openScenario(pid: number | string, id: number): Promise<void> {
      const p = this._p(pid)
      if (p.tabs.some((t) => t.id === id)) {
        this.activate(pid, id)
        return
      }
      const key = `${pid}:${id}`
      if (_pending.has(key)) return
      _pending.add(key)
      try {
        const s = await apifoxApi.getScenario(id)
        if (!p.tabs.some((t) => t.id === id)) p.tabs.push(newTab(s))
        this.activate(pid, id)
      } finally {
        _pending.delete(key)
      }
    },
    async reloadScenario(pid: number | string, id: number): Promise<void> {
      const t = this.findTab(pid, id)
      if (!t) return
      const s = await apifoxApi.getScenario(id)
      t.form = scenarioToForm(s)
      t.snapshot = snap(t.form)
      t.version = s.version ?? 1
      t.name = s.name
    },
    closeTab(pid: number | string, id: number): void {
      const p = this._p(pid)
      const idx = p.tabs.findIndex((t) => t.id === id)
      if (idx < 0) return
      p.tabs.splice(idx, 1)
      if (p.activeId === id) {
        const last = p.tabs.find((t) => t.id === p.lastActiveId)
        p.activeId = last ? last.id : p.tabs.length ? p.tabs[p.tabs.length - 1]!.id : null
      }
      if (p.lastActiveId === id) p.lastActiveId = null
    },
    afterSave(pid: number | string, id: number, version?: number): void {
      const t = this.findTab(pid, id)
      if (!t) return
      if (version != null) t.version = version
      t.name = t.form.name
      t.snapshot = snap(t.form)
    },
    onRenamed(pid: number | string, id: number, name: string): void {
      const t = this.findTab(pid, id)
      if (!t) return
      t.name = name
      t.form.name = name
      t.snapshot = snap(t.form)
    },
  },
})

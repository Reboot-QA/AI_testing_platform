import { defineStore } from 'pinia'
import { apifoxApi } from '@/api'

export interface SuiteForm {
  id: number
  name: string
  description: string
  items: any[]
}

export interface SuiteTab {
  id: number
  name: string
  form: SuiteForm
  snapshot: string
  version: number
  running: boolean
  runEvents: unknown[]
  saving: boolean
}

interface ProjectTabsState {
  tabs: SuiteTab[]
  activeId: number | null
  lastActiveId: number | null
}

let _uid = 0
const nextUid = (): string => `si-${_uid++}`

function suiteToForm(s: any): SuiteForm {
  return {
    id: s.id,
    name: s.name,
    description: s.description || '',
    items: (s.items || []).map((it: any) => ({ ...it, _uid: nextUid() })),
  }
}

// 脏检测快照：只序列化会保存的字段（_uid 为前端拖拽键，随加载稳定，纳入无碍）
const snap = (f: SuiteForm): string =>
  JSON.stringify({ name: f.name, description: f.description, items: f.items })

const _pending = new Set<string>()

function newTab(s: any): SuiteTab {
  const form = suiteToForm(s)
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

export const useSuiteTabsStore = defineStore('suiteTabs', {
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
    findTab(pid: number | string, id: number | null): SuiteTab | null {
      return this._p(pid).tabs.find((t) => t.id === id) || null
    },
    isDirty(tab: SuiteTab | null): boolean {
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
    async openSuite(pid: number | string, id: number): Promise<void> {
      const p = this._p(pid)
      if (p.tabs.some((t) => t.id === id)) {
        this.activate(pid, id)
        return
      }
      const key = `${pid}:${id}`
      if (_pending.has(key)) return
      _pending.add(key)
      try {
        const s = await apifoxApi.getSuite(id)
        if (!p.tabs.some((t) => t.id === id)) p.tabs.push(newTab(s))
        this.activate(pid, id)
      } finally {
        _pending.delete(key)
      }
    },
    async reloadSuite(pid: number | string, id: number): Promise<void> {
      const t = this.findTab(pid, id)
      if (!t) return
      const s = await apifoxApi.getSuite(id)
      t.form = suiteToForm(s)
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
  },
})

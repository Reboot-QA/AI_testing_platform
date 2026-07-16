import { defineStore } from 'pinia'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'
import { normalizeSpec } from '@/utils/apifoxSpec'
import type { RequestSpec } from '@/types/apifox'

type Endpoint = Schemas['EndpointOut']

export interface EndpointForm {
  id: number
  name: string
  method: string
  path: string
  server_name: string | null
  description: string
  request_spec: RequestSpec
  assertions: unknown[]
  extracts: unknown[]
  pre_scripts: unknown[]
  post_scripts: unknown[]
  response_schema_id: number | null
  contract_strict: boolean
}

export interface ApiTab {
  id: number
  name: string
  method: string
  form: EndpointForm
  snapshot: string
  version: number
  endpointTab: string
  saving: boolean
}

interface ProjectTabsState {
  tabs: ApiTab[]
  activeId: number | null
  lastActiveId: number | null
}

function endpointToForm(e: Endpoint): EndpointForm {
  return {
    id: e.id,
    name: e.name,
    method: e.method,
    path: e.path,
    server_name: e.server_name || null,
    description: e.description || '',
    request_spec: normalizeSpec(e.request_spec),
    assertions: e.assertions || [],
    extracts: e.extracts || [],
    pre_scripts: e.pre_scripts || [],
    post_scripts: e.post_scripts || [],
    response_schema_id: e.response_schema_id || null,
    contract_strict: e.contract_strict || false,
  }
}

const snap = (form: EndpointForm): string => JSON.stringify(form)

const _pending = new Set<string>()

function newTab(e: Endpoint): ApiTab {
  const form = endpointToForm(e)
  return {
    id: e.id,
    name: e.name,
    method: e.method,
    form,
    snapshot: snap(form),
    version: e.version ?? 1,
    endpointTab: 'debug',
    saving: false,
  }
}

export const useApiTabsStore = defineStore('apiTabs', {
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
    findTab(pid: number | string, id: number): ApiTab | null {
      return this._p(pid).tabs.find((t) => t.id === id) || null
    },
    isDirty(tab: ApiTab | null): boolean {
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
    async openEndpoint(pid: number | string, id: number): Promise<void> {
      const p = this._p(pid)
      if (p.tabs.some((t) => t.id === id)) {
        this.activate(pid, id)
        return
      }
      const key = `${pid}:${id}`
      if (_pending.has(key)) return
      _pending.add(key)
      try {
        const e = await apifoxApi.getEndpoint(id)
        if (!p.tabs.some((t) => t.id === id)) p.tabs.push(newTab(e))
        this.activate(pid, id)
      } finally {
        _pending.delete(key)
      }
    },
    async reloadEndpoint(pid: number | string, id: number): Promise<void> {
      const t = this.findTab(pid, id)
      if (!t) return
      const e = await apifoxApi.getEndpoint(id)
      t.form = endpointToForm(e)
      t.snapshot = snap(t.form)
      t.version = e.version ?? 1
      t.name = e.name
      t.method = e.method
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
    afterSave(pid: number | string, id: number, updated?: Partial<Endpoint>): void {
      const t = this.findTab(pid, id)
      if (!t) return
      if (updated?.version != null) t.version = updated.version
      t.name = t.form.name
      t.method = t.form.method
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

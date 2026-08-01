import { defineStore } from 'pinia'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'
import { emptySpec, normalizeSpec } from '@/utils/apifoxSpec'
import { deriveEndpointProcessors } from '@/utils/caseProcessors'
import type { EndpointForm } from '@/types/apifox'

type Endpoint = Schemas['EndpointOut']
type ProcessorRow = Schemas['ProcessorRow']

export type { EndpointForm } from '@/types/apifox'

interface ApiTab {
  id: number
  name: string
  method: string
  form: EndpointForm
  snapshot: string
  version: number
  endpointTab: string
  saving: boolean
  /** 草稿态：尚未落库的新接口，保存时才 create（见 openDraft/promoteDraft） */
  draft?: boolean
  /** 草稿创建到哪个目录下（null=根） */
  folderId?: number | null
  /** 最近一次调试响应；切走其它接口再切回仍保留，不丢结果（7/23-#5） */
  debugResp?: Schemas['DebugResponse'] | null
}

interface ProjectTabsState {
  tabs: ApiTab[]
  activeId: number | null
  lastActiveId: number | null
  /** 已加载过的接口后置处理器缓存（tab 关闭后仍供 {{ 联想） */
  extractProcessorsByEndpoint: Record<number, ProcessorRow[]>
}

function endpointToForm(e: Endpoint): EndpointForm {
  const form: EndpointForm = {
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
    pre_processors: e.pre_processors || [],
    post_processors: e.post_processors || [],
    response_schema_id: e.response_schema_id || null,
    contract_strict: e.contract_strict || false,
  }
  deriveEndpointProcessors(form) // 存量接口无处理器时由旧字段派生（含契约），须在快照前
  return form
}

const snap = (form: EndpointForm): string => JSON.stringify(form)

const _pending = new Set<string>()

// 草稿 tab 用递减的负 id 占位，永不与真实接口 id（正数）冲突；保存后由 promoteDraft 换成真 id
let _draftSeq = -1

function blankDraftForm(id: number): EndpointForm {
  return {
    id,
    name: '',
    method: 'GET',
    path: '/',
    server_name: null,
    description: '',
    request_spec: emptySpec(),
    assertions: [],
    extracts: [],
    pre_scripts: [],
    post_scripts: [],
    pre_processors: [],
    post_processors: [],
    response_schema_id: null,
    contract_strict: false,
  }
}

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

function touchExtractCatalog(p: ProjectTabsState, endpointId: number, form: EndpointForm): void {
  p.extractProcessorsByEndpoint[endpointId] = [...(form.post_processors ?? [])]
}

export const useApiTabsStore = defineStore('apiTabs', {
  state: () => ({ byProject: {} as Record<string, ProjectTabsState> }),
  getters: {
    tabsOf: (s) => (pid: number | string) => s.byProject[String(pid)]?.tabs || [],
    activeIdOf: (s) => (pid: number | string) => s.byProject[String(pid)]?.activeId ?? null,
    /** 项目内所有已打开 + 曾打开过的接口后置处理器（供跨接口 {{ 联想） */
    projectPostProcessors:
      (s) =>
      (pid: number | string): ProcessorRow[] => {
        const p = s.byProject[String(pid)]
        if (!p) return []
        const openIds = new Set(p.tabs.map((t) => t.id))
        const fromOpen = p.tabs.flatMap((t) => t.form.post_processors ?? [])
        const fromClosed = Object.entries(p.extractProcessorsByEndpoint)
          .filter(([id]) => !openIds.has(Number(id)))
          .flatMap(([, procs]) => procs ?? [])
        return [...fromOpen, ...fromClosed]
      },
  },
  actions: {
    _p(pid: number | string): ProjectTabsState {
      const k = String(pid)
      if (!this.byProject[k]) {
        this.byProject[k] = {
          tabs: [],
          activeId: null,
          lastActiveId: null,
          extractProcessorsByEndpoint: {},
        }
      }
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
    /** 取消当前接口激活态，保留已打开 tab，供点击接口树空白区使用。 */
    deactivate(pid: number | string): void {
      const p = this._p(pid)
      if (p.activeId != null) p.lastActiveId = p.activeId
      p.activeId = null
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
        if (!p.tabs.some((t) => t.id === id)) {
          const tab = newTab(e)
          p.tabs.push(tab)
          touchExtractCatalog(p, id, tab.form)
        }
        this.activate(pid, id)
      } finally {
        _pending.delete(key)
      }
    },
    /** 新建接口草稿：不落库，先开一个空 tab，填内容/调试后由 saveEndpoint 走 create */
    openDraft(pid: number | string, folderId: number | null = null): number {
      const p = this._p(pid)
      const id = _draftSeq--
      const form = blankDraftForm(id)
      const tab: ApiTab = {
        id,
        name: '',
        method: 'GET',
        form,
        snapshot: snap(form), // 初始不脏：未改动直接关闭不弹确认
        version: 0,
        endpointTab: 'debug',
        saving: false,
        draft: true,
        folderId,
      }
      p.tabs.push(tab)
      this.activate(pid, id)
      return id
    },
    /** 草稿保存成功后：把临时 tab 换成真实接口（id/version/快照对齐，活动态跟随） */
    promoteDraft(pid: number | string, tempId: number, created: Endpoint): void {
      const p = this._p(pid)
      const t = p.tabs.find((x) => x.id === tempId)
      if (!t) return
      t.id = created.id
      t.form.id = created.id
      t.draft = false
      t.folderId = undefined
      t.version = created.version ?? 1
      t.name = t.form.name
      t.method = t.form.method
      t.snapshot = snap(t.form)
      if (p.activeId === tempId) p.activeId = created.id
      if (p.lastActiveId === tempId) p.lastActiveId = created.id
      touchExtractCatalog(p, created.id, t.form)
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
      touchExtractCatalog(this._p(pid), id, t.form)
    },
    closeTab(pid: number | string, id: number): void {
      const p = this._p(pid)
      const idx = p.tabs.findIndex((t) => t.id === id)
      if (idx < 0) return
      touchExtractCatalog(p, id, p.tabs[idx]!.form)
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
      touchExtractCatalog(this._p(pid), id, t.form)
    },
    onRenamed(pid: number | string, id: number, name: string, version?: number): void {
      const t = this.findTab(pid, id)
      if (!t) return
      t.name = name
      t.form.name = name
      // 同步树改名后的新版本号，避免详情再保存时用过期 version 误报冲突（7/23-#6）
      if (version != null) t.version = version
      t.snapshot = snap(t.form)
    },

    /** 记住某接口最近一次调试响应，供组件重挂载(切走切回)后恢复（7/23-#5） */
    setDebugResp(pid: number | string, id: number, resp: Schemas['DebugResponse'] | null): void {
      const t = this.findTab(pid, id)
      if (t) t.debugResp = resp
    },

    /** 切换账号/退出登录时清空：tab 按项目缓存，不清会把上个用户的接口带到新会话 */
    resetAll(): void {
      this.byProject = {}
    },
  },
})

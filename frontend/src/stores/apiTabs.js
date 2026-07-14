import { defineStore } from 'pinia'
import { apifoxApi } from '@/api'
import { normalizeSpec } from '@/utils/apifoxSpec'

// 接口管理「同时打开多个接口」的多标签状态（借鉴 Apifox-UI：tabs + activeId + lastActiveId）。
// 存 Pinia 而非组件内：切主 tab 会销毁 ApiManage，Pinia 存活可保留已打开的接口 tab 与编辑态。
// 按项目隔离。dirty 用「初始快照深比较」判定（快照存 JSON 串）。

function endpointToForm(e) {
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

const snap = (form) => JSON.stringify(form)

function newTab(e) {
  const form = endpointToForm(e)
  return {
    id: e.id,
    name: e.name,
    method: e.method,
    form,
    snapshot: snap(form),
    version: e.version ?? 1,
    endpointTab: 'debug', // 接口内子 tab（调试/文档/用例）各 tab 独立
  }
}

export const useApiTabsStore = defineStore('apiTabs', {
  state: () => ({ byProject: {} }),
  getters: {
    tabsOf: (s) => (pid) => s.byProject[String(pid)]?.tabs || [],
    activeIdOf: (s) => (pid) => s.byProject[String(pid)]?.activeId ?? null,
  },
  actions: {
    _p(pid) {
      const k = String(pid)
      if (!this.byProject[k]) this.byProject[k] = { tabs: [], activeId: null, lastActiveId: null }
      return this.byProject[k]
    },
    findTab(pid, id) {
      return this._p(pid).tabs.find((t) => t.id === id) || null
    },
    isDirty(tab) {
      return !!tab && snap(tab.form) !== tab.snapshot
    },
    hasAnyDirty(pid) {
      return this._p(pid).tabs.some((t) => this.isDirty(t))
    },
    activate(pid, id) {
      const p = this._p(pid)
      if (p.activeId !== id) {
        p.lastActiveId = p.activeId
        p.activeId = id
      }
    },
    async openEndpoint(pid, id) {
      const p = this._p(pid)
      if (p.tabs.some((t) => t.id === id)) {
        this.activate(pid, id)
        return
      }
      const e = await apifoxApi.getEndpoint(id)
      p.tabs.push(newTab(e))
      this.activate(pid, id)
    },
    async reloadEndpoint(pid, id) {
      const t = this.findTab(pid, id)
      if (!t) return
      const e = await apifoxApi.getEndpoint(id)
      t.form = endpointToForm(e)
      t.snapshot = snap(t.form)
      t.version = e.version ?? 1
      t.name = e.name
      t.method = e.method
    },
    closeTab(pid, id) {
      const p = this._p(pid)
      const idx = p.tabs.findIndex((t) => t.id === id)
      if (idx < 0) return
      p.tabs.splice(idx, 1)
      if (p.activeId === id) {
        // 优先回退上一次激活的 tab，否则激活末尾
        const last = p.tabs.find((t) => t.id === p.lastActiveId)
        p.activeId = last ? last.id : (p.tabs.at(-1)?.id ?? null)
      }
      if (p.lastActiveId === id) p.lastActiveId = null
    },
    // 保存成功：重置快照(清脏) + 回写 version + 同步展示名/方法
    afterSave(pid, id, updated) {
      const t = this.findTab(pid, id)
      if (!t) return
      if (updated?.version != null) t.version = updated.version
      t.name = t.form.name
      t.method = t.form.method
      t.snapshot = snap(t.form)
    },
    // 树上重命名/删除的联动
    onRenamed(pid, id, name) {
      const t = this.findTab(pid, id)
      if (!t) return
      t.name = name
      t.form.name = name
      t.snapshot = snap(t.form)
    },
  },
})

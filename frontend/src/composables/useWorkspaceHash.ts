import { onBeforeUnmount, onMounted, reactive, watch } from 'vue'
import { useRoute } from 'vue-router'
import type {
  AutomationBiz,
  SettingsSection,
  WorkspaceDomain,
  WorkspaceHashState,
} from '@/types/shell'

// 深链照搬原型 project.html 的 hash 语义（方案 A：project 走路由 path 参数，其余走 hash）：
//   /hub/workspace/:projectId#domain=&section=&biz=&open=
//   - settings 域用 open，不写 section/biz
//   - automation 域才有 biz；其它域不写 biz/open
//   - 同值不重复写回（避免多余 hashchange）

const DOMAINS: readonly string[] = ['requirements', 'functional', 'automation', 'settings']
const BIZ_LIST: readonly string[] = ['apis', 'autotest', 'reports', 'ai']
const SETTINGS_LIST: readonly string[] = [
  'basic',
  'scripts',
  'sql-scripts',
  'datasets',
  'databases',
  'notify',
  'envs',
  'members',
  'import',
  'export',
]
const AUTOTEST_SECTIONS = new Set([
  'overview',
  'cases',
  'scenarios',
  'suites',
  'schedules',
  'datamodels',
  'trash',
])

function isApiSection(s: string): boolean {
  return s === 'apis' || s.startsWith('ep-')
}

function inferBiz(section: string): AutomationBiz {
  if (section === 'reports') return 'reports'
  if (section === 'ai') return 'ai'
  if (isApiSection(section)) return 'apis'
  return 'autotest'
}

function defaultSectionForBiz(biz: AutomationBiz): string {
  if (biz === 'apis') return 'apis'
  if (biz === 'reports') return 'reports'
  if (biz === 'ai') return 'ai'
  return 'overview'
}

function isValidSectionForBiz(biz: AutomationBiz, section: string): boolean {
  if (biz === 'apis') return isApiSection(section)
  if (biz === 'reports') return section === 'reports'
  if (biz === 'ai') return section === 'ai'
  return (
    AUTOTEST_SECTIONS.has(section) ||
    section.startsWith('case-') ||
    section.startsWith('scn-') ||
    section.startsWith('suite-')
  )
}

function toDomain(v: string | null): WorkspaceDomain {
  return v && DOMAINS.includes(v) ? (v as WorkspaceDomain) : 'automation'
}

function toBiz(v: string | null): AutomationBiz | null {
  return v && BIZ_LIST.includes(v) ? (v as AutomationBiz) : null
}

function toSettings(v: string | null): SettingsSection {
  // 旧书签 open=data → 导入数据
  if (v === 'data') return 'import'
  return v && SETTINGS_LIST.includes(v) ? (v as SettingsSection) : 'basic'
}

function defaultSectionForDomain(domain: WorkspaceDomain): string {
  if (domain === 'requirements') return 'req-overview'
  if (domain === 'functional') return 'func-overview'
  return 'overview'
}

function readParams(): URLSearchParams {
  return new URLSearchParams(window.location.hash.replace(/^#/, ''))
}

/** 概览 tile / 最近 AI 列表跳转时写入的列表筛选（hash filter=） */
export function readWorkspaceListFilter(): string | null {
  return readParams().get('filter')
}

export function readWorkspaceRunId(): number | null {
  const raw = readParams().get('run')
  if (!raw) return null
  const id = Number(raw)
  return Number.isFinite(id) && id > 0 ? id : null
}

function serialize(state: WorkspaceHashState): string {
  const p = new URLSearchParams()
  p.set('domain', state.domain)
  if (state.domain === 'settings') {
    p.set('open', state.open)
  } else if (state.domain === 'automation') {
    p.set('biz', state.biz)
    p.set('section', state.section)
  } else {
    p.set('section', state.section)
  }
  if (state.filter) p.set('filter', state.filter)
  if (state.run) p.set('run', String(state.run))
  return p.toString()
}

export function useWorkspaceHash() {
  const state = reactive<WorkspaceHashState>({
    domain: 'automation',
    section: 'overview',
    biz: 'autotest',
    open: 'basic',
    filter: undefined,
    run: undefined,
  })

  function parse() {
    const p = readParams()
    state.domain = toDomain(p.get('domain'))
    state.filter = p.get('filter') || undefined
    const runId = readWorkspaceRunId()
    state.run = runId ?? undefined
    if (state.domain === 'settings') {
      const rawOpen = p.get('open')
      state.open = toSettings(rawOpen)
      // 旧书签 open=data 归一为 import 并回写 hash
      if (rawOpen === 'data') sync()
      return
    }
    if (state.domain === 'automation') {
      const section = p.get('section') || ''
      let biz = toBiz(p.get('biz'))
      if (!biz) biz = section ? inferBiz(section) : 'autotest'
      state.biz = biz
      state.section =
        section && isValidSectionForBiz(biz, section) ? section : defaultSectionForBiz(biz)
      return
    }
    state.section = p.get('section') || defaultSectionForDomain(state.domain)
  }

  function sync() {
    const next = serialize(state)
    if (readParams().toString() !== next) {
      window.location.hash = next
    }
  }

  function switchDomain(domain: WorkspaceDomain) {
    state.domain = domain
    state.run = undefined
    if (domain === 'automation' && !isValidSectionForBiz(state.biz, state.section)) {
      state.section = defaultSectionForBiz(state.biz)
    } else if (domain === 'requirements' || domain === 'functional') {
      state.section = defaultSectionForDomain(domain)
    }
    sync()
  }

  function switchBiz(biz: AutomationBiz, section?: string) {
    state.domain = 'automation'
    state.run = undefined
    state.biz = biz
    const target = section ?? state.section
    state.section = isValidSectionForBiz(biz, target) ? target : defaultSectionForBiz(biz)
    sync()
  }

  function setSection(section: string, filter?: string | null) {
    state.run = undefined
    if (filter !== undefined) {
      state.filter = filter || undefined
    } else {
      state.filter = undefined
    }
    if (state.domain === 'automation') {
      const biz = inferBiz(section)
      state.biz = biz
      state.section = isValidSectionForBiz(biz, section) ? section : defaultSectionForBiz(biz)
    } else {
      state.section = section
    }
    sync()
  }

  function setSettings(open: SettingsSection) {
    state.domain = 'settings'
    state.open = open
    sync()
  }

  // 两种 hash 变更来源都要响应：① 内部导航 sync() 直写 window.location.hash → hashchange 事件；
  // ② 路由驱动（如 AI 助手 router.push 深链）走 pushState 不触发 hashchange → 监听 route.fullPath。
  // parse() 幂等，双触发无副作用。
  const route = useRoute()
  watch(() => route.fullPath, parse)

  onMounted(() => {
    parse()
    window.addEventListener('hashchange', parse)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('hashchange', parse)
  })

  return { state, switchDomain, switchBiz, setSection, setSettings }
}

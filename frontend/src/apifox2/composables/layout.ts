import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'

/** 对应 Apifox-UI 的 contexts/layout-settings。 */
export interface Apifox2LayoutContext {
  isSideMenuCollapsed: Ref<boolean>
  /** 折叠侧边菜单面板。 */
  collapse: () => void
  /** 展开侧边菜单面板。 */
  expand: () => void
  /** 注册面板的折叠/展开控制函数（由 PanelLayout 提供）。 */
  registerPanelControls: (controls: { collapse: () => void; expand: () => void }) => void
}

const KEY: InjectionKey<Apifox2LayoutContext> = Symbol('apifox2-layout')

export function provideApifox2Layout(): Apifox2LayoutContext {
  const isSideMenuCollapsed = ref(false)

  let panelControls: { collapse: () => void; expand: () => void } | null = null

  const ctx: Apifox2LayoutContext = {
    isSideMenuCollapsed,
    collapse: () => panelControls?.collapse(),
    expand: () => panelControls?.expand(),
    registerPanelControls: (controls) => {
      panelControls = controls
    },
  }

  provide(KEY, ctx)

  return ctx
}

export function useApifox2Layout(): Apifox2LayoutContext {
  const ctx = inject(KEY)

  if (!ctx) {
    throw new Error('useApifox2Layout 必须在 provideApifox2Layout 之下使用')
  }

  return ctx
}

// @bytemd/vue-next 自带的类型把组件错误地导出为 DefineComponent「类型」，
// 导致在 verbatimModuleSyntax 下 Editor/Viewer 被当作 type-only。
// 这里补充它们的「值」声明，使其可作为组件正常导入使用。
declare module '@bytemd/vue-next' {
  import type { DefineComponent } from 'vue'
  export const Editor: DefineComponent<Record<string, unknown>>
  export const Viewer: DefineComponent<Record<string, unknown>>
}

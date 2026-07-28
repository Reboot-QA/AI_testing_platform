import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    permission?: string
    anyPermissions?: string[]
    public?: boolean
    title?: string
    sectionTitle?: string
  }
}

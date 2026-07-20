/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<object, object, unknown>
  export default component
}

declare module '*?worker' {
  const WorkerFactory: {
    new (): Worker
  }
  export default WorkerFactory
}

declare module 'monaco-editor/esm/vs/editor/editor.api'
declare module 'monaco-editor/esm/vs/language/json/monaco.contribution'
declare module 'monaco-editor/esm/vs/basic-languages/javascript/javascript.contribution'
declare module 'monaco-editor/esm/vs/basic-languages/python/python.contribution'

interface ImportMetaEnv {
  readonly VITE_API_TARGET?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface MonacoEnvironment {
  getWorker(workerId: string, label: string): Worker
}

declare global {
  interface Window {
    MonacoEnvironment?: MonacoEnvironment
  }

  // eslint-disable-next-line no-var
  var MonacoEnvironment: MonacoEnvironment | undefined
}

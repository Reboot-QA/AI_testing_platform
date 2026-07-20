import { loader } from '@guolao/vue-monaco-editor'

let initPromise: Promise<unknown> | null = null

export function ensureMonaco(): Promise<unknown> {
  if (initPromise) return initPromise
  initPromise = (async () => {
    const monaco = await import('monaco-editor/esm/vs/editor/editor.api')
    await Promise.all([
      import('monaco-editor/esm/vs/language/json/monaco.contribution'),
      import('monaco-editor/esm/vs/basic-languages/javascript/javascript.contribution'),
      import('monaco-editor/esm/vs/basic-languages/python/python.contribution'),
    ])
    const EditorWorker = (await import('monaco-editor/esm/vs/editor/editor.worker?worker')).default
    const JsonWorker = (await import('monaco-editor/esm/vs/language/json/json.worker?worker'))
      .default
    self.MonacoEnvironment = {
      getWorker(_workerId: string, label: string): Worker {
        if (label === 'json') return new JsonWorker()
        return new EditorWorker()
      },
    }
    loader.config({ monaco })
    return monaco
  })()
  return initPromise
}

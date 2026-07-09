// Monaco 本地化 + 懒加载：全程走 npm 包与本地 worker，绝不请求外部 CDN（平台本地部署无外网）。
// 模块级 promise 保证多个编辑器实例只初始化一次。
import { loader } from '@guolao/vue-monaco-editor'

let initPromise = null

export function ensureMonaco() {
  if (initPromise) return initPromise
  initPromise = (async () => {
    const monaco = await import('monaco-editor')
    const EditorWorker = (await import('monaco-editor/esm/vs/editor/editor.worker?worker')).default
    const JsonWorker = (await import('monaco-editor/esm/vs/language/json/json.worker?worker')).default
    const TsWorker = (await import('monaco-editor/esm/vs/language/typescript/ts.worker?worker')).default
    self.MonacoEnvironment = {
      getWorker(_workerId, label) {
        if (label === 'json') return new JsonWorker()
        if (label === 'typescript' || label === 'javascript') return new TsWorker()
        return new EditorWorker()
      },
    }
    loader.config({ monaco })
    return monaco
  })()
  return initPromise
}

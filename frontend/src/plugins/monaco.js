// Monaco 本地化 + 懒加载 + 按需裁剪：只装编辑器核心 + JSON 语言服务 + JS/Python 语法高亮，
// 不引入完整 monaco-editor（否则会打包 ts/html/css worker 等海量用不到的模块，撑爆构建内存）。
// 全程走 npm 包与本地 worker，绝不请求外部 CDN（平台本地部署无外网）。
// 模块级 promise 保证多个编辑器实例只初始化一次。
import { loader } from '@guolao/vue-monaco-editor'

let initPromise = null

export function ensureMonaco() {
  if (initPromise) return initPromise
  initPromise = (async () => {
    // editor.api 只含编辑器核心（不含任何语言服务），语言按需单独 contribute。
    const monaco = await import('monaco-editor/esm/vs/editor/editor.api')
    await Promise.all([
      // JSON：完整语言服务（校验/格式化/补全，配 json.worker）
      import('monaco-editor/esm/vs/language/json/monaco.contribution'),
      // JS/Python：仅语法高亮（basic-languages，无 worker）
      import('monaco-editor/esm/vs/basic-languages/javascript/javascript.contribution'),
      import('monaco-editor/esm/vs/basic-languages/python/python.contribution'),
    ])
    const EditorWorker = (await import('monaco-editor/esm/vs/editor/editor.worker?worker')).default
    const JsonWorker = (await import('monaco-editor/esm/vs/language/json/json.worker?worker')).default
    self.MonacoEnvironment = {
      getWorker(_workerId, label) {
        if (label === 'json') return new JsonWorker()
        return new EditorWorker()
      },
    }
    loader.config({ monaco })
    return monaco
  })()
  return initPromise
}

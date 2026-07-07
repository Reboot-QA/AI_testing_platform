const handlers = new Map()

export function registerAssistantHandler(name, fn) {
  handlers.set(name, fn)
}

export function unregisterAssistantHandler(name) {
  handlers.delete(name)
}

export async function invokeAssistantHandler(name, payload = {}) {
  const handler = handlers.get(name)
  if (!handler) {
    throw new Error(`未注册的操作处理器：${name}`)
  }
  return handler(payload)
}

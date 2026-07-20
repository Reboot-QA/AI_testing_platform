export type AssistantActionHandler = (
  payload?: Record<string, unknown>,
) => unknown | Promise<unknown>

const handlers = new Map<string, AssistantActionHandler>()

export function registerAssistantHandler(name: string, fn: AssistantActionHandler): void {
  handlers.set(name, fn)
}

export function unregisterAssistantHandler(name: string): void {
  handlers.delete(name)
}

export async function invokeAssistantHandler(
  name: string,
  payload: Record<string, unknown> = {},
): Promise<unknown> {
  const handler = handlers.get(name)
  if (!handler) {
    throw new Error(`未注册的操作处理器：${name}`)
  }
  return handler(payload)
}

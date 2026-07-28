import { streamSSE, type SSEEvent } from './request'
import type { Schemas } from './types'

export const assistantApi = {
  chatStream: (
    data: Schemas['AssistantChatRequest'],
    onEvent: (event: SSEEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) =>
    streamSSE('/api/v1/assistant/chat/stream', {
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' },
      signal: options.signal,
      onEvent,
    }),
}

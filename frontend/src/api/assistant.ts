import { streamSSE, type SSEEvent } from './request'
import type { Schemas } from './types'

export const assistantApi = {
  chatStream: <TEvent extends SSEEvent>(
    data: Schemas['AssistantChatRequest'],
    onEvent: (event: TEvent) => void,
    options: { signal?: AbortSignal } = {},
  ) =>
    streamSSE<TEvent>('/api/v1/assistant/chat/stream', {
      body: JSON.stringify(data),
      headers: { 'Content-Type': 'application/json' },
      signal: options.signal,
      onEvent,
    }),
}

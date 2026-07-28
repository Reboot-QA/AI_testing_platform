export const ASSISTANT_CHAT_STORAGE_KEY = 'assistant-chat-messages-v1'
export const MAX_STORED_ASSISTANT_MESSAGES = 80

export interface StoredAssistantMessage {
  id: string
  role: string
  content: string
  actions?: unknown
  actionStatus?: unknown
  executionLogs?: unknown
  actionError?: unknown
}

export interface AssistantMessageStore {
  messages: StoredAssistantMessage[]
  messageSeq: number
}

export function clearAssistantChat(): void {
  localStorage.removeItem(ASSISTANT_CHAT_STORAGE_KEY)
}

export function loadAssistantMessages({
  createMessageId: _createMessageId,
  normalizeMessage,
}: {
  createMessageId: (seq: number) => string
  normalizeMessage: (raw: unknown) => StoredAssistantMessage
}): AssistantMessageStore {
  try {
    const raw = localStorage.getItem(ASSISTANT_CHAT_STORAGE_KEY)
    if (!raw) return { messages: [], messageSeq: 0 }
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return { messages: [], messageSeq: 0 }
    const normalized = parsed.map(normalizeMessage)
    const maxId = normalized.reduce((max, item) => {
      const match = String(item.id).match(/-(\d+)$/)
      return match ? Math.max(max, Number(match[1])) : max
    }, 0)
    return {
      messages: normalized.slice(-MAX_STORED_ASSISTANT_MESSAGES),
      messageSeq: maxId,
    }
  } catch {
    return { messages: [], messageSeq: 0 }
  }
}

export function saveAssistantMessages(messages: StoredAssistantMessage[]): void {
  const payload = messages.slice(-MAX_STORED_ASSISTANT_MESSAGES).map((item) => ({
    id: item.id,
    role: item.role,
    content: item.content,
    actions: item.actions,
    actionStatus: item.actionStatus,
    executionLogs: item.executionLogs,
    actionError: item.actionError,
  }))
  localStorage.setItem(ASSISTANT_CHAT_STORAGE_KEY, JSON.stringify(payload))
}

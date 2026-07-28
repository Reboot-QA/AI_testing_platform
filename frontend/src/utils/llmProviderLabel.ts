import type { Schemas } from '@/api/types'

export function formatLlmProviderLabel(item: Schemas['LLMProviderOptionOut']): string {
  const tags: string[] = []
  if (item.is_default) tags.push('默认')
  if (!item.api_key_configured) tags.push('未配置Key')
  const suffix = tags.length ? ` (${tags.join(' / ')})` : ''
  return `${item.name}${suffix}`
}

export function splitParenHighlightParts(text: string): string[] {
  return text.split(/(\([^)]+\))/g).filter((part) => part.length > 0)
}

export function isParenHighlightPart(part: string): boolean {
  return part.startsWith('(') && part.endsWith(')')
}

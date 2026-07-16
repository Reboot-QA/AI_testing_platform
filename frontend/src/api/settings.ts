import { del, get, post, put, type Id } from './request'
import type { Schemas } from './types'

export const settingsApi = {
  getLLM: () => get<Schemas['LLMSettingsOut']>('/settings/llm'),
  getLLMOptions: () => get<Schemas['LLMGenerateOptionsOut']>('/settings/llm/options'),
  updateMockMode: (mock_mode: Schemas['MockModeUpdate']['mock_mode']) =>
    put<Schemas['LLMSettingsOut']>('/settings/llm/mock', { mock_mode }),
  createProvider: (data: Schemas['LLMProviderCreate']) =>
    post<Schemas['LLMProviderOut']>('/settings/llm/providers', data),
  updateProvider: (id: Id, data: Schemas['LLMProviderUpdate']) =>
    put<Schemas['LLMProviderOut']>(`/settings/llm/providers/${id}`, data),
  deleteProvider: (id: Id) => del<any>(`/settings/llm/providers/${id}`), // 无 response_model（技术债）
  activateProvider: (id: Id) =>
    put<Schemas['LLMProviderOut']>(`/settings/llm/providers/${id}/activate`),
  testLLM: (data?: Schemas['LLMTestRequest']) =>
    post<Schemas['LLMTestResponse']>('/settings/llm/test', data || {}),
}

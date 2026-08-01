/** AI 任务域（与自动化同级）侧栏 section */
export const AI_TASKS_SECTIONS = new Set([
  'ai',
  'ai-overview',
  'ai-req',
  'ai-case',
  'ai-api',
])

export function normalizeAiTasksSection(section: string): string {
  if (section === 'ai') return 'ai-api'
  if (AI_TASKS_SECTIONS.has(section)) return section
  return 'ai-overview'
}

export function isValidAiTasksSection(section: string): boolean {
  return AI_TASKS_SECTIONS.has(section)
}

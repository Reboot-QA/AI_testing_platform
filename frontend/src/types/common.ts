import type { ProjectPageOut } from '@/api/project'
import type { Schemas } from '@/api/types'

export type Project = Schemas['ProjectOut']
export type Requirement = Schemas['RequirementOut']
export type TestCase = Schemas['TestCaseOut']
export type User = Schemas['UserOut']
export type Department = Schemas['DepartmentOut']
export type DashboardStats = Schemas['DashboardStats']
export type LlmProvider = Schemas['LLMProviderOut']

export type ProjectPage = ProjectPageOut

export type PageResult<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
}

export type RequirementPage = PageResult<Requirement>
export type TestCasePage = PageResult<TestCase>

export type Id = number | string
export type DateInput = string | Date | null | undefined

export const ALL_PROJECTS = '__all__' as const
export type ProjectFilter = typeof ALL_PROJECTS | number

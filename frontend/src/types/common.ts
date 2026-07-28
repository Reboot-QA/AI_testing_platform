import type { ProjectPageOut } from '@/api/project'
import type { Schemas } from '@/api/types'

export type { Id } from '@/api/request'

export type Project = Schemas['ProjectOut']
export type Requirement = Schemas['RequirementOut']
export type TestCase = Schemas['TestCaseOut']
export type User = Schemas['UserOut']
export type Department = Schemas['DepartmentOut']
export type DashboardStats = Schemas['DashboardStats']
export type LlmProvider = Schemas['LLMProviderOut']

export type ReviewStatus = 'draft' | 'pending' | 'approved' | 'rejected'
export type RequirementStatus = 'draft' | 'approved' | 'closed'

export type ProjectPage = ProjectPageOut

export type PageResult<T> = {
  items: T[]
  total: number
  page: number
  page_size: number
}

export type RequirementPage = PageResult<Requirement>
export type TestCasePage = PageResult<TestCase>

export type DateInput = string | Date | null | undefined

export const ALL_PROJECTS = '__all__' as const
export type ProjectFilter = typeof ALL_PROJECTS | number

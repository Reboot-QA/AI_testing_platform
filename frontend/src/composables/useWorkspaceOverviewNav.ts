import { toValue, type MaybeRefOrGetter } from 'vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'
import type { Id } from '@/api/request'
import { legacyWorkspaceRouteFromParts } from '@/router/workspace'
import type { WorkspaceDomain } from '@/types/shell'

export type WorkspaceNavPayload = {
  domain: WorkspaceDomain
  section: string
  filter?: string
  query?: Record<string, string>
}

export function workspaceRouteLocation(
  projectId: Id,
  domain: WorkspaceDomain,
  section: string,
  filter?: string,
  extraQuery: Record<string, string> = {},
): RouteLocationRaw | null {
  const query: Record<string, string> = { ...extraQuery }
  if (filter) query.filter = filter
  const target = legacyWorkspaceRouteFromParts(domain, section, query)
  if (!target) return null
  return {
    name: target.name,
    params: { projectId: String(projectId) },
    query: target.query,
  }
}

/** 工作区概览页内跳转子页面（需求/功能/自动化/AI 任务）。 */
export function useWorkspaceOverviewNav(
  projectId: MaybeRefOrGetter<Id>,
  domain: WorkspaceDomain,
) {
  const router = useRouter()

  function navigate(
    section: string,
    filter?: string,
    extraQuery: Record<string, string> = {},
  ) {
    const location = workspaceRouteLocation(
      toValue(projectId),
      domain,
      section,
      filter,
      extraQuery,
    )
    if (location) void router.push(location)
  }

  return { navigate }
}

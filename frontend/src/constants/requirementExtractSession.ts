export const REQ_EXTRACT_CTX_KEY = 'testhub:req-extract-ctx'

export type ReqExtractPersistedCtx = {
  projectId: number
  hubTaskId: number
  target: string
}

export function readReqExtractCtx(projectId: number): ReqExtractPersistedCtx | null {
  try {
    const raw = sessionStorage.getItem(REQ_EXTRACT_CTX_KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as ReqExtractPersistedCtx
    if (data?.projectId !== projectId || !data.hubTaskId) return null
    return data
  } catch {
    return null
  }
}

export function writeReqExtractCtx(ctx: ReqExtractPersistedCtx): void {
  sessionStorage.setItem(REQ_EXTRACT_CTX_KEY, JSON.stringify(ctx))
}

export function clearReqExtractCtx(projectId?: number): void {
  if (projectId == null) {
    sessionStorage.removeItem(REQ_EXTRACT_CTX_KEY)
    return
  }
  const cur = readReqExtractCtx(projectId)
  if (cur) sessionStorage.removeItem(REQ_EXTRACT_CTX_KEY)
}

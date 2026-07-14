// apifox 请求规格（request_spec）的空模板与归一化。三处(ApiManage/AutoTests/ApiCasesPanel)共用。
import { ensureKvRows } from '@/utils/apiCaseConfig'

export function emptySpec() {
  return {
    query: [],
    path_params: [],
    headers: [],
    cookies: [],
    body: { type: 'none', raw: '', form: [], graphql_query: '', graphql_variables: '' },
    auth: { type: 'none', token: '', username: '', password: '' },
  }
}

export function normalizeSpec(spec) {
  const s = spec || {}
  const b = s.body || {}
  return {
    query: ensureKvRows(s.query || []),
    path_params: ensureKvRows(s.path_params || []),
    headers: ensureKvRows(s.headers || []),
    cookies: ensureKvRows(s.cookies || []),
    body: {
      type: b.type || 'none',
      raw: b.raw || '',
      form: ensureKvRows(b.form || []),
      graphql_query: b.graphql_query || '',
      graphql_variables: b.graphql_variables || '',
    },
    auth: {
      type: s.auth?.type || 'none',
      token: s.auth?.token || '',
      username: s.auth?.username || '',
      password: s.auth?.password || '',
    },
  }
}

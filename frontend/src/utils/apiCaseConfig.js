const META_KEY = '__meta'

export const DEFAULT_ASSERTIONS = '[{"type":"status_code","expected":200}]'

export function emptyKvRow() {
  return { key: '', value: '', enabled: true, desc: '' }
}

export function emptyExtractRow() {
  return { key: '', source: 'body', path: '$.code', enabled: true, desc: '' }
}

export function ensureExtractRows(rows) {
  return rows?.length ? rows.map((row) => ({
    key: row.key || '',
    source: row.source || 'body',
    path: row.path || '',
    enabled: row.enabled !== false,
    desc: row.desc || '',
  })) : [emptyExtractRow()]
}

export function countActiveExtractRows(rows) {
  return (rows || []).filter((row) => row.enabled !== false && row.key?.trim() && row.path?.trim()).length
}

export const PRE_OPERATION_OPTIONS = [
  {
    type: 'script',
    label: '自定义脚本',
    color: '#67c23a',
    description: '在请求发送前运行脚本，将结果写入 variables，供 URL / Header / Body 中 {{变量名}} 引用',
  },
  {
    type: 'database',
    label: '数据库',
    color: '#409eff',
    description: '连接数据库执行 SQL，查询结果可写入 variables，供后续步骤引用（执行引擎后续接入）',
  },
  {
    type: 'wait',
    label: '等待',
    color: '#e6a23c',
    description: '暂停指定毫秒后继续执行后续操作',
  },
]

export const POST_OPERATION_OPTIONS = [
  {
    type: 'script',
    label: '自定义脚本',
    color: '#67c23a',
    description: '在请求完成后运行脚本，可读取响应并写入 variables',
  },
  {
    type: 'database',
    label: '数据库',
    color: '#409eff',
    description: '连接数据库执行 SQL，查询结果可写入 variables，供后续步骤引用（执行引擎后续接入）',
  },
  {
    type: 'assertion',
    label: '断言',
    color: '#f56c6c',
    description: '校验响应状态码、JSON 字段、Header 等是否符合预期',
  },
  {
    type: 'extract',
    label: '提取变量',
    color: '#9b59b6',
    description: '从响应体或响应头提取字段到 variables，套件执行时后续用例可引用',
  },
  {
    type: 'wait',
    label: '等待',
    color: '#e6a23c',
    description: '暂停指定毫秒后继续执行后续操作',
  },
]

const SINGLETON_POST_TYPES = new Set(['assertion', 'extract'])
const SINGLETON_PRE_TYPES = new Set([])

export function createOperationId() {
  return `op_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

export function emptyDatabaseConfig() {
  return {
    driver: 'mysql',
    host: '127.0.0.1',
    port: 3306,
    database: '',
    username: '',
    password: '',
    sql: '',
  }
}

export function createOperation(type, partial = {}) {
  const base = {
    id: partial.id || createOperationId(),
    type,
    enabled: partial.enabled !== false,
  }
  switch (type) {
    case 'script':
      return {
        ...base,
        lang: partial.lang || 'javascript',
        stores: {
          javascript: partial.stores?.javascript ?? '',
          python: partial.stores?.python ?? '',
        },
      }
    case 'wait':
      return { ...base, ms: Number(partial.ms) > 0 ? Number(partial.ms) : 1000 }
    case 'database':
      return { ...base, db: { ...emptyDatabaseConfig(), ...(partial.db || {}) } }
    case 'assertion':
      return { ...base, content: partial.content ?? DEFAULT_ASSERTIONS }
    case 'extract':
      return {
        ...base,
        expanded: Boolean(partial.expanded),
        rows: ensureExtractRows(partial.rows),
      }
    default:
      return base
  }
}

export function normalizeOperation(raw) {
  if (!raw?.type) return null
  return createOperation(raw.type, raw)
}

function hasScriptContent(stores) {
  return Boolean(stores?.javascript?.trim() || stores?.python?.trim())
}

export function operationHasContent(operation) {
  if (!operation || operation.enabled === false) return false
  switch (operation.type) {
    case 'script':
      return hasScriptContent(operation.stores)
    case 'wait':
      return Number(operation.ms) > 0
    case 'database':
      return Boolean(
        operation.db?.sql?.trim() ||
          operation.db?.host?.trim() ||
          operation.db?.database?.trim()
      )
    case 'assertion':
      return Boolean((operation.content || '').trim())
    case 'extract':
      return countActiveExtractRows(operation.rows) > 0
    default:
      return false
  }
}

function legacyPreOperations(preScriptStores, preScriptLang) {
  if (hasScriptContent(preScriptStores)) {
    return [createOperation('script', { lang: preScriptLang, stores: preScriptStores })]
  }
  return []
}

function sanitizeStoredPostOperations(operations) {
  return operations.filter((operation) => {
    if (operation.type !== 'assertion') return true
    const text = (operation.content || '').trim()
    return text && normalizeJsonText(text) !== normalizeJsonText(DEFAULT_ASSERTIONS)
  })
}

export function parsePreOperations(meta, preScriptStores, preScriptLang) {
  const stored = (meta?.pre_operations || []).map(normalizeOperation).filter(Boolean)
  if (stored.length) return stored
  return legacyPreOperations(preScriptStores, preScriptLang)
}

export function parsePostOperations(meta, postScript, extractRows, assertions) {
  const stored = sanitizeStoredPostOperations(
    (meta?.post_operations || []).map(normalizeOperation).filter(Boolean)
  )
  if (stored.length) return stored

  const ops = []
  if (postScript?.trim()) {
    const stores = emptyPreScriptStores()
    stores.javascript = postScript
    ops.push(createOperation('script', { stores, lang: 'javascript' }))
  }
  if (countActiveExtractRows(extractRows) > 0) {
    ops.push(createOperation('extract', { rows: extractRows }))
  }
  const assertionText = (assertions || '').trim()
  if (
    assertionText &&
    normalizeJsonText(assertionText) !== normalizeJsonText(DEFAULT_ASSERTIONS)
  ) {
    ops.push(createOperation('assertion', { content: assertions }))
  }
  return ops
}

export function syncLegacyFromOperations(preOperations = [], postOperations = []) {
  const preScriptOp = preOperations.find((item) => item.type === 'script')
  const postScriptOp = postOperations.find((item) => item.type === 'script')
  const assertionOp = postOperations.find((item) => item.type === 'assertion')
  const extractOps = postOperations.filter((item) => item.type === 'extract')
  const extractRows = extractOps.length
    ? ensureExtractRows(extractOps.flatMap((item) => item.rows || []))
    : [emptyExtractRow()]

  return {
    preScriptStores: preScriptOp?.stores || emptyPreScriptStores(),
    preScriptLang: preScriptOp?.lang || 'javascript',
    postScript: postScriptOp ? activePreScript(postScriptOp.stores, postScriptOp.lang || 'javascript') : '',
    extractRows,
    assertions: assertionOp?.content || DEFAULT_ASSERTIONS,
    preOperations,
    postOperations,
  }
}

export function canAddOperation(operations, type, phase) {
  const singletons = phase === 'pre' ? SINGLETON_PRE_TYPES : SINGLETON_POST_TYPES
  if (singletons.has(type)) {
    return !operations.some((item) => item.type === type)
  }
  return true
}

export function normalizeJsonText(text) {
  try {
    return JSON.stringify(JSON.parse(text))
  } catch {
    return (text || '').trim()
  }
}

function unwrapJsonStringNode(node) {
  if (typeof node !== 'string') return node
  try {
    const parsed = JSON.parse(node)
    return typeof parsed === 'object' && parsed !== null ? parsed : node
  } catch {
    return node
  }
}

function resolveJsonPath(data, path) {
  if (!path) return { found: true, value: data }

  let normalized = path.trim()
  if (normalized.startsWith('$.')) normalized = normalized.slice(2)
  else if (normalized.startsWith('$')) normalized = normalized.slice(1).replace(/^\./, '')

  let current = data
  const parts = normalized.replace(/\[(\d+)\]/g, '.$1').split('.').filter(Boolean)

  for (const part of parts) {
    if (current == null) return { found: false, value: undefined }

    current = unwrapJsonStringNode(current)

    if (Array.isArray(current)) {
      if (!/^\d+$/.test(part)) return { found: false, value: undefined }
      const index = Number(part)
      if (index >= current.length) return { found: false, value: undefined }
      current = current[index]
      continue
    }

    if (typeof current === 'object') {
      if (!Object.prototype.hasOwnProperty.call(current, part)) {
        return { found: false, value: undefined }
      }
      current = current[part]
      continue
    }

    return { found: false, value: undefined }
  }

  return { found: true, value: current }
}

function getValueByJsonPath(data, path) {
  const { found, value } = resolveJsonPath(data, path)
  return found ? value : undefined
}

export function jsonPathExists(data, path) {
  return resolveJsonPath(data, path).found
}

function findFieldPathInJson(data, fieldName, currentPath = '$') {
  if (data == null || !fieldName) return null

  const node = unwrapJsonStringNode(data)

  if (Array.isArray(node)) {
    for (let index = 0; index < node.length; index += 1) {
      const found = findFieldPathInJson(node[index], fieldName, `${currentPath}[${index}]`)
      if (found) return found
    }
    return null
  }

  if (typeof node === 'object') {
    if (Object.prototype.hasOwnProperty.call(node, fieldName)) {
      return `${currentPath}.${fieldName}`
    }
    for (const [key, value] of Object.entries(node)) {
      const found = findFieldPathInJson(value, fieldName, `${currentPath}.${key}`)
      if (found) return found
    }
  }

  return null
}

export function looksLikeRequestBody(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return false

  const responseHints = ['code', 'msg', 'message', 'success', 'errno', 'errorCode']
  const requestHints = ['solidLetterPower', 'securityUpgrade', 'deviceNo', 'platformType', 'client']
  const hasResponseHint = responseHints.some((key) => Object.prototype.hasOwnProperty.call(data, key))
  const requestHintCount = requestHints.filter((key) => Object.prototype.hasOwnProperty.call(data, key)).length

  if (requestHintCount >= 2 && !hasResponseHint) return true

  const dataJson = data.dataJson
  if (dataJson && typeof dataJson === 'object' && 'password' in dataJson && !hasResponseHint) {
    return true
  }

  return false
}

export function listExtractableFieldPaths(data, limit = 20) {
  const paths = []

  function walk(node, currentPath) {
    if (paths.length >= limit) return
    const value = unwrapJsonStringNode(node)

    if (Array.isArray(value)) {
      value.forEach((item, index) => walk(item, `${currentPath}[${index}]`))
      return
    }

    if (value && typeof value === 'object') {
      Object.entries(value).forEach(([key, child]) => {
        const nextPath = `${currentPath}.${key}`
        if (child !== null && typeof child === 'object') {
          walk(child, nextPath)
        } else {
          paths.push(nextPath)
        }
      })
    }
  }

  walk(data, '$')
  return paths.slice(0, limit)
}

/**
 * 根据返回 JSON 与提取字段生成 JSON Path 表达式。
 * 需先提供完整响应 JSON，再输入字段名（如 msg、code）或点路径（如 data.token）。
 */
export function buildExtractExpression(fieldInput, responseBody = '') {
  const text = (fieldInput || '').trim()
  if (!text) {
    throw new Error('请输入提取字段')
  }
  if (!responseBody?.trim()) {
    throw new Error('请先粘贴接口返回 JSON')
  }

  let parsed
  try {
    parsed = JSON.parse(responseBody)
  } catch {
    throw new Error('返回 JSON 格式不正确')
  }

  if (looksLikeRequestBody(parsed)) {
    throw new Error('当前粘贴内容更像请求体，请粘贴接口响应 JSON，或点击「填入最近响应」')
  }

  let path = ''
  let variableName = ''

  if (text.startsWith('$.')) {
    path = text
    const segments = text.slice(2).split(/\.|\[|\]/).filter(Boolean)
    variableName = segments[segments.length - 1] || ''
  } else if (text.startsWith('$[')) {
    path = text
    const match = text.match(/([^.\[\]]+)(?!.*[.\[])/)
    variableName = match?.[1] || ''
  } else if (text.includes('.') || text.includes('[')) {
    const normalized = text.replace(/^\./, '')
    path = normalized.startsWith('$') ? normalized : `$.${normalized}`
    const segments = path.replace(/^\$\.?/, '').split(/\.|\[|\]/).filter(Boolean)
    variableName = segments[segments.length - 1] || ''
  } else {
    variableName = text
    path = `$.${text}`
  }

  let actual = getValueByJsonPath(parsed, path)
  let matched = actual !== undefined

  if (!matched) {
    const autoPath = findFieldPathInJson(parsed, variableName)
    if (autoPath) {
      path = autoPath
      actual = getValueByJsonPath(parsed, path)
      matched = actual !== undefined
    }
  }

  if (!matched) {
    const suggestions = listExtractableFieldPaths(parsed, 8)
    const hint = suggestions.length ? `。可提取字段示例：${suggestions.join('、')}` : ''
    throw new Error(`在返回 JSON 中未找到字段「${text}」${hint}`)
  }

  let previewValue = ''
  if (actual !== undefined && actual !== null) {
    previewValue = typeof actual === 'object' ? JSON.stringify(actual) : String(actual)
  }

  if (!variableName) {
    const segments = path.replace(/^\$\.?/, '').split(/\.|\[|\]/).filter(Boolean)
    variableName = segments[segments.length - 1] || text
  }

  return {
    path,
    variableName,
    matched: true,
    previewValue,
  }
}

export function emptyPreScriptStores() {
  return { javascript: '', python: '' }
}

export function parsePreScriptStores(meta) {
  const lang = meta?.pre_script_lang || 'javascript'
  const stored = meta?.pre_script_stores || {}
  const stores = {
    javascript: stored.javascript ?? '',
    python: stored.python ?? '',
  }
  const legacy = meta?.pre_script || ''
  if (legacy.trim()) {
    const key = lang === 'python' ? 'python' : 'javascript'
    if (!stores[key].trim()) {
      stores[key] = legacy
    }
  }
  return stores
}

export function activePreScript(stores, lang) {
  const key = lang === 'python' ? 'python' : 'javascript'
  return stores?.[key] || ''
}

export function variablesMapFromRows(variableRows) {
  const map = {}
  ;(variableRows || []).forEach((row) => {
    const name = (row.key || '').trim()
    if (!name || row.enabled === false) return
    map[name] = row.value ?? ''
  })
  return map
}

export function emptyDataDriveRow(variableNames = []) {
  const values = {}
  variableNames.forEach((name) => {
    values[name] = ''
  })
  return { enabled: true, name: '', values }
}

export function variableNamesFromRows(variableRows) {
  return (variableRows || [])
    .filter((row) => row.enabled !== false && (row.key || '').trim())
    .map((row) => row.key.trim())
}

export function defaultValuesFromRows(variableRows) {
  const values = {}
  ;(variableRows || []).forEach((row) => {
    const name = (row.key || '').trim()
    if (!name || row.enabled === false) return
    values[name] = row.value ?? ''
  })
  return values
}

export function ensureDataDriveRows(rows, variableNames) {
  const list = Array.isArray(rows) ? rows : []
  if (!list.length) return [emptyDataDriveRow(variableNames)]
  return list.map((row) => ({
    enabled: row.enabled !== false,
    name: row.name || '',
    values: {
      ...Object.fromEntries(variableNames.map((name) => [name, ''])),
      ...(row.values || {}),
    },
  }))
}

export function parseCsvDataSets(text, variableNames) {
  const lines = (text || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  if (!lines.length) throw new Error('CSV 内容为空')

  const splitLine = (line) => {
    const cells = []
    let current = ''
    let inQuotes = false
    for (let i = 0; i < line.length; i += 1) {
      const ch = line[i]
      if (ch === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"'
          i += 1
        } else {
          inQuotes = !inQuotes
        }
      } else if (ch === ',' && !inQuotes) {
        cells.push(current.trim())
        current = ''
      } else {
        current += ch
      }
    }
    cells.push(current.trim())
    return cells
  }

  const headerCells = splitLine(lines[0])
  const hasHeader = headerCells.some((cell) => variableNames.includes(cell))
  const dataLines = hasHeader ? lines.slice(1) : lines
  const headers = hasHeader ? headerCells : variableNames

  if (!dataLines.length) throw new Error('CSV 没有数据行')

  return dataLines.map((line, index) => {
    const cells = splitLine(line)
    const values = {}
    headers.forEach((header, idx) => {
      const name = (header || '').trim()
      if (!name) return
      values[name] = cells[idx] ?? ''
    })
    return {
      enabled: true,
      name: `数据集${index + 1}`,
      values,
    }
  })
}

export function parseJsonDataSets(text, variableNames) {
  const parsed = JSON.parse((text || '').trim())
  if (!Array.isArray(parsed) || !parsed.length) {
    throw new Error('请输入 JSON 数组')
  }
  return parsed.map((item, index) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) {
      throw new Error(`第 ${index + 1} 行必须是对象`)
    }
    const values = {}
    variableNames.forEach((name) => {
      values[name] = item[name] == null ? '' : String(item[name])
    })
    Object.entries(item).forEach(([key, value]) => {
      const name = String(key || '').trim()
      if (!name) return
      values[name] = value == null ? '' : String(value)
    })
    return {
      enabled: true,
      name: item.name ? String(item.name) : `数据集${index + 1}`,
      values,
    }
  })
}

const CONTENT_TYPE_BY_BODY = {
  json: 'application/json',
  'form-data': 'multipart/form-data',
  urlencoded: 'application/x-www-form-urlencoded',
}

export function ensureKvRows(rows) {
  return rows?.length ? rows : [emptyKvRow()]
}

export function countActiveKvRows(rows) {
  return (rows || []).filter((r) => r.enabled !== false && r.key?.trim()).length
}

export function enrichHeaderRows(headerRows, bodyType) {
  const rows = (headerRows || []).map((row) => ({ ...row }))
  const hasKey = (name) =>
    rows.some((r) => r.enabled !== false && r.key?.trim().toLowerCase() === name.toLowerCase())

  const contentType = CONTENT_TYPE_BY_BODY[bodyType]
  if (contentType && !hasKey('content-type')) {
    rows.push({ key: 'Content-Type', value: contentType, enabled: true, desc: '' })
  }

  const meaningful = rows.filter((r) => r.key?.trim())
  return ensureKvRows(meaningful)
}

export function parseCaseConfig(headersText, bodyText, assertions = DEFAULT_ASSERTIONS) {
  let headersObj = {}
  try {
    headersObj = headersText ? JSON.parse(headersText) : {}
  } catch {
    headersObj = {}
  }

  const meta = headersObj[META_KEY] || {}
  delete headersObj[META_KEY]

  let headerRows = Object.entries(headersObj).map(([key, value]) => ({
    key,
    value: value == null ? '' : String(value),
    enabled: true,
    desc: '',
  }))

  let auth = meta.auth || { type: 'none', token: '', username: '', password: '' }
  const authHeader = headerRows.find((r) => r.key.toLowerCase() === 'authorization')
  if (auth.type === 'none' && authHeader?.value) {
    if (authHeader.value.startsWith('Bearer ')) {
      auth = { type: 'bearer', token: authHeader.value.slice(7).trim(), username: '', password: '' }
    } else if (authHeader.value.startsWith('Basic ')) {
      auth = { type: 'basic', token: '', username: '', password: '' }
    }
  }
  headerRows = headerRows.filter((r) => !['authorization', 'cookie'].includes(r.key.toLowerCase()))

  const bodyType = resolveBodyType(meta.body_type, bodyText)
  const formBodyRows = meta.form_body || []
  const bodyStores = parseBodyStores(meta, bodyType, bodyText, formBodyRows)

  const variableRowsParsed = ensureKvRows(meta.variables || [])
  const variableNames = variableNamesFromRows(variableRowsParsed)

  return {
    headerRows: enrichHeaderRows(headerRows, bodyType),
    queryRows: ensureKvRows(meta.query || []),
    pathRows: ensureKvRows(meta.path_vars || []),
    cookieRows: ensureKvRows(meta.cookies || []),
    auth,
    bodyType,
    formBodyRows: ensureKvRows(formBodyRows),
    bodyStores,
    variableRows: variableRowsParsed,
    dataDriveEnabled: Boolean(meta.data_drive?.enabled),
    dataDriveRows: ensureDataDriveRows(meta.data_drive?.rows || [], variableNames),
    extractRows: ensureExtractRows(meta.response_extract || []),
    preScriptStores: parsePreScriptStores(meta),
    preScriptLang: meta.pre_script_lang || 'javascript',
    postScript: meta.post_script || '',
    preOperations: parsePreOperations(meta, parsePreScriptStores(meta), meta.pre_script_lang || 'javascript'),
    postOperations: parsePostOperations(
      meta,
      meta.post_script || '',
      ensureExtractRows(meta.response_extract || []),
      assertions
    ),
  }
}

function isKvBodyArray(value) {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((item) => item && typeof item === 'object' && 'key' in item)
  )
}

export function inferBodyType(body) {
  if (!body || !body.trim()) return 'none'
  const text = body.trim()
  try {
    const parsed = JSON.parse(text)
    if (isKvBodyArray(parsed)) return 'form-data'
  } catch {
    /* not valid json */
  }
  if (text.startsWith('{') || text.startsWith('[')) return 'json'
  return 'raw'
}

function resolveBodyType(metaBodyType, bodyText) {
  const hasBody = Boolean(bodyText?.trim())
  if (!hasBody) return metaBodyType || 'none'

  const inferred = inferBodyType(bodyText)
  if (!metaBodyType || metaBodyType === 'none') return inferred

  if (metaBodyType === 'form-data' || metaBodyType === 'urlencoded') {
    try {
      const parsed = JSON.parse(bodyText.trim())
      if (isKvBodyArray(parsed)) return metaBodyType
    } catch {
      /* fall through */
    }
    return inferred
  }

  return metaBodyType
}

export function emptyBodyStores() {
  return {
    json: '',
    raw: '',
    urlencoded: [emptyKvRow()],
    formData: [emptyKvRow()],
  }
}

export function parseBodyStores(meta, bodyType, bodyText, legacyFormBodyRows = []) {
  const stored = meta?.body_stores || {}
  const stores = {
    json: stored.json ?? '',
    raw: stored.raw ?? '',
    urlencoded: ensureKvRows(stored.urlencoded || []),
    formData: ensureKvRows(stored.form_data || []),
  }

  if (bodyType === 'json' && bodyText?.trim() && !stores.json.trim()) {
    stores.json = bodyText
  }
  if (bodyType === 'raw' && bodyText?.trim() && !stores.raw.trim()) {
    stores.raw = bodyText
  }
  if (bodyType === 'urlencoded' && !countActiveKvRows(stores.urlencoded)) {
    stores.urlencoded = bodyContentFromStored('urlencoded', bodyText, legacyFormBodyRows)
  }
  if (bodyType === 'form-data' && !countActiveKvRows(stores.formData)) {
    stores.formData = bodyContentFromStored('form-data', bodyText, legacyFormBodyRows)
  }

  return stores
}

function filterFormRows(rows) {
  return (rows || []).filter((r) => (r.key || '').trim())
}

export function applyVariables(text, variables) {
  if (!text || !variables?.length) return text ?? ''
  const map = {}
  variables.forEach(({ key, value, enabled }) => {
    const name = (key || '').trim()
    if (!name || enabled === false) return
    map[name] = value ?? ''
  })
  if (!Object.keys(map).length) return String(text)
  return String(text).replace(/\{\{([^}]+)\}\}/g, (match, name) => {
    const key = name.trim()
    return Object.prototype.hasOwnProperty.call(map, key) ? map[key] : match
  })
}

export function serializeCaseConfig({
  headerRows,
  queryRows,
  pathRows,
  cookieRows,
  variableRows,
  dataDriveEnabled,
  dataDriveRows,
  extractRows,
  auth,
  bodyType,
  bodyStores,
  formBodyRows,
  preScriptStores,
  preScriptLang,
  postScript,
  preOperations,
  postOperations,
  path,
  rawBody = '',
}) {
  const synced = syncLegacyFromOperations(preOperations || [], postOperations || [])
  const resolvedPreScriptStores = synced.preScriptStores
  const resolvedPreScriptLang = synced.preScriptLang
  const resolvedPostScript = synced.postScript
  const resolvedExtractRows = synced.extractRows
  const resolvedPreOperations = synced.preOperations
  const resolvedPostOperations = synced.postOperations
  const stores = bodyStores || emptyBodyStores()
  const activeFormRows =
    bodyType === 'form-data'
      ? stores.formData
      : bodyType === 'urlencoded'
        ? stores.urlencoded
        : formBodyRows || []
  const activeRawBody =
    bodyType === 'json' ? stores.json : bodyType === 'raw' ? stores.raw : rawBody
  const headersObj = {}

  headerRows.forEach(({ key, value, enabled }) => {
    const k = (key || '').trim()
    if (!k || enabled === false) return
    if (['authorization', 'cookie', 'content-type'].includes(k.toLowerCase())) return
    headersObj[k] = value ?? ''
  })

  headersObj[META_KEY] = {
    query: queryRows.filter((r) => (r.key || '').trim()),
    path_vars: pathRows.filter((r) => (r.key || '').trim()),
    cookies: cookieRows.filter((r) => (r.key || '').trim()),
    variables: filterFormRows(variableRows || []),
    data_drive: {
      enabled: Boolean(dataDriveEnabled),
      rows: (dataDriveRows || [])
        .filter((row) => row && (row.name?.trim() || Object.values(row.values || {}).some((v) => String(v ?? '').trim())))
        .map((row) => ({
          enabled: row.enabled !== false,
          name: (row.name || '').trim(),
          values: row.values || {},
        })),
    },
    response_extract: (extractRows || resolvedExtractRows || [])
      .filter((row) => (row.key || '').trim() && (row.path || '').trim())
      .map((row) => ({
        key: row.key.trim(),
        source: row.source || 'body',
        path: row.path.trim(),
        enabled: row.enabled !== false,
        desc: row.desc || '',
      })),
    auth,
    body_type: bodyType,
    form_body: filterFormRows(activeFormRows),
    body_stores: {
      json: stores.json || '',
      raw: stores.raw || '',
      urlencoded: filterFormRows(stores.urlencoded),
      form_data: filterFormRows(stores.formData),
    },
    pre_script: activePreScript(resolvedPreScriptStores || emptyPreScriptStores(), resolvedPreScriptLang),
    pre_script_lang: resolvedPreScriptLang || 'javascript',
    pre_script_stores: {
      javascript: (resolvedPreScriptStores || emptyPreScriptStores()).javascript || '',
      python: (resolvedPreScriptStores || emptyPreScriptStores()).python || '',
    },
    post_script: resolvedPostScript || '',
    pre_operations: resolvedPreOperations,
    post_operations: resolvedPostOperations,
  }

  const body = buildBody(bodyType, activeFormRows, activeRawBody)
  const finalPath = applyPathAndQuery(path, pathRows, queryRows)

  return {
    path: finalPath,
    headers: JSON.stringify(headersObj, null, 2),
    body,
  }
}

export function buildBody(bodyType, formBodyRows, rawBody) {
  if (bodyType === 'none') return ''
  if (bodyType === 'json' || bodyType === 'raw') return rawBody || ''
  const rows = formBodyRows.filter((r) => r.enabled !== false && (r.key || '').trim())
  if (bodyType === 'form-data' || bodyType === 'urlencoded') {
    return JSON.stringify(rows.map((r) => ({ key: r.key.trim(), value: r.value ?? '' })))
  }
  return rawBody || ''
}

export function applyPathAndQuery(path, pathRows, queryRows) {
  let result = path || '/'
  pathRows.forEach(({ key, value, enabled }) => {
    const k = (key || '').trim()
    if (!k || enabled === false) return
    result = result.replace(`{${k}}`, encodeURIComponent(value ?? ''))
  })

  const [pathname, existingQuery] = result.split('?', 2)
  const params = new URLSearchParams(existingQuery || '')
  queryRows.forEach(({ key, value, enabled }) => {
    const k = (key || '').trim()
    if (!k || enabled === false) return
    params.set(k, value ?? '')
  })
  const qs = params.toString()
  return qs ? `${pathname}?${qs}` : pathname
}

export function splitUrlForEditor(fullUrl, env) {
  const text = (fullUrl || '').trim()
  if (!text) {
    return {
      pathWithoutQuery: '/',
      queryRows: ensureKvRows([]),
      pathRows: ensureKvRows([]),
    }
  }

  try {
    const parsed = new URL(text.includes('://') ? text : `https://placeholder.local${text.startsWith('/') ? '' : '/'}${text}`)
    const queryRows = []
    parsed.searchParams.forEach((value, key) => {
      queryRows.push({ key, value, enabled: true, desc: '' })
    })

    const pathRows = []
    const varMatches = parsed.pathname.match(/\{([^}]+)\}/g) || []
    varMatches.forEach((token) => {
      pathRows.push({ key: token.slice(1, -1), value: '', enabled: true, desc: '' })
    })

    let pathWithoutQuery = `${parsed.origin}${parsed.pathname}`
    const base = env?.base_url ? new URL(env.base_url) : null
    if (base && parsed.origin === base.origin) {
      pathWithoutQuery = parsed.pathname || '/'
    } else if (!text.includes('://') && text.startsWith('/')) {
      pathWithoutQuery = parsed.pathname || '/'
    }

    return {
      pathWithoutQuery,
      queryRows: ensureKvRows(queryRows),
      pathRows: ensureKvRows(pathRows),
    }
  } catch {
    const [pathname, queryString] = text.split('?', 2)
    const queryRows = []
    if (queryString) {
      const params = new URLSearchParams(queryString)
      params.forEach((value, key) => {
        queryRows.push({ key, value, enabled: true, desc: '' })
      })
    }
    return {
      pathWithoutQuery: pathname || '/',
      queryRows: ensureKvRows(queryRows),
      pathRows: ensureKvRows([]),
    }
  }
}

export function displayUrlFromSplit(split, env) {
  const path = split.pathWithoutQuery || '/'
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }
  const base = (env?.base_url || '').replace(/\/$/, '')
  const segment = path.startsWith('/') ? path : `/${path}`
  return base ? `${base}${segment}` : segment
}

export function bodyContentFromStored(bodyType, bodyText, formBodyRows) {
  if (bodyType === 'form-data' || bodyType === 'urlencoded') {
    if (formBodyRows?.length && formBodyRows.some((r) => r.key?.trim())) return formBodyRows
    try {
      const parsed = JSON.parse(bodyText || '[]')
      if (Array.isArray(parsed)) {
        return ensureKvRows(parsed.map((i) => ({ key: i.key, value: i.value, enabled: true, desc: '' })))
      }
      if (parsed && typeof parsed === 'object') {
        return jsonToFormBodyRows(JSON.stringify(parsed))
      }
    } catch {
      /* ignore */
    }
    return [emptyKvRow()]
  }
  return bodyText || ''
}

function stringifyFormFieldValue(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  if (typeof value === 'boolean') return value ? 'true' : 'false'
  return String(value)
}

export function jsonToFormBodyRows(jsonText) {
  const parsed = JSON.parse((jsonText || '').trim())
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('请输入 JSON 对象')
  }
  return Object.entries(parsed).map(([key, value]) => ({
    key,
    value: stringifyFormFieldValue(value),
    enabled: true,
    desc: '',
  }))
}

function stripJsonLiteralQuotes(text) {
  let s = String(text ?? '').trim()
  while (s.endsWith(',')) s = s.slice(0, -1).trim()
  s = s.replace(/\\"/g, '"')
  if (s.length >= 2 && s.startsWith('"') && s.endsWith('"')) {
    s = s.slice(1, -1).trim()
  }
  return s
}

function parseFormFieldValue(text) {
  const trimmed = stripJsonLiteralQuotes(text)
  if (!trimmed) return ''
  if (trimmed === '{') return '{'
  if (trimmed === '}') return '}'
  if (trimmed === 'true') return true
  if (trimmed === 'false') return false
  if (trimmed === 'null') return null
  if (/^-?\d+(\.\d+)?$/.test(trimmed)) return Number(trimmed)
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    try {
      return JSON.parse(trimmed)
    } catch {
      return trimmed
    }
  }
  return trimmed
}

function isNestedFieldKey(key) {
  return /^[a-z][a-z0-9_]*$/.test(key)
}

export function formRowsToJson(rows) {
  const list = (rows || []).filter((r) => r.enabled !== false && stripJsonLiteralQuotes(r.key))
  const obj = {}
  let i = 0

  while (i < list.length) {
    const key = stripJsonLiteralQuotes(list[i].key)
    const rawValue = list[i].value
    const parsedValue = parseFormFieldValue(rawValue)

    if (!key || key === '}' || parsedValue === '}') {
      i += 1
      continue
    }

    if (parsedValue === '{') {
      const nested = {}
      i += 1
      while (i < list.length) {
        const nestedKey = stripJsonLiteralQuotes(list[i].key)
        const nestedValue = parseFormFieldValue(list[i].value)
        if (!nestedKey || nestedKey === '}' || nestedValue === '}') {
          i += 1
          break
        }
        if (nestedKey in obj || !isNestedFieldKey(nestedKey)) {
          break
        }
        nested[nestedKey] = nestedValue
        i += 1
      }
      obj[key] = nested
      continue
    }

    obj[key] = parsedValue
    i += 1
  }

  return JSON.stringify(obj, null, 2)
}

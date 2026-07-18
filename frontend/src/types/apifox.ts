/** Apifox 请求规格、用例配置、操作编排等 UI 层共享类型 */

import type { Schemas } from '@/api/types'
import { emptySpec } from '@/utils/apifoxSpec'

export type KvValueType = 'string' | 'number' | 'boolean' | 'file'

export interface KvRow {
  key: string
  value: string
  enabled: boolean
  desc: string
  type?: KvValueType | string
  source?: string
}

export type ExtractSource =
  | 'response_json'
  | 'response_xml'
  | 'response_text'
  | 'response_header'
  | 'response_cookie'
  | 'response_time'
  | 'request_header'
  | 'request_body'

export interface ExtractSourceOption {
  value: ExtractSource
  label: string
  pathLabel: string
  placeholder: string
}

export type VariableScope = 'temporary' | 'environment' | 'global' | 'case' | 'extract'

export interface ExtractRow {
  key: string
  path: string
  enabled: boolean
  desc: string
  scope: VariableScope | string
  source?: ExtractSource | string
}

export type OperationPhase = 'pre' | 'post'

export type OperationType = 'script' | 'wait' | 'database' | 'assertion' | 'extract'

export interface OperationOption {
  type: OperationType
  label: string
  color: string
  description: string
}

export interface ScriptStores {
  javascript: string
  python: string
}

export interface DatabaseConfig {
  driver: string
  host: string
  port: number
  database: string
  username: string
  password: string
  sql: string
}

export interface OperationBase {
  id: string
  type: OperationType
  enabled: boolean
}

export interface ScriptOperation extends OperationBase {
  type: 'script'
  lang: string
  stores: ScriptStores
}

export interface WaitOperation extends OperationBase {
  type: 'wait'
  ms: number
}

export interface DatabaseOperation extends OperationBase {
  type: 'database'
  db: DatabaseConfig
}

export interface AssertionOperation extends OperationBase {
  type: 'assertion'
  content: string
}

export interface ExtractOperation extends OperationBase {
  type: 'extract'
  expanded?: boolean
  source: ExtractSource | string
  rows: ExtractRow[]
}

export type Operation =
  | ScriptOperation
  | WaitOperation
  | DatabaseOperation
  | AssertionOperation
  | ExtractOperation
  | OperationBase

export type BodyType = 'none' | 'json' | 'raw' | 'form' | 'graphql' | 'file' | 'urlencoded' | string

export interface RequestBody {
  type: BodyType
  raw: string
  form: KvRow[]
  graphql_query: string
  graphql_variables: string
  file_id: number | null
  file_name: string
}

export interface AuthConfig {
  type: string
  token: string
  username: string
  password: string
}

export interface RequestSettings {
  timeout_ms: number | null
  verify_ssl: boolean
  follow_redirects: boolean
}

export interface RequestSpec {
  query: KvRow[]
  path_params: KvRow[]
  headers: KvRow[]
  cookies: KvRow[]
  body: RequestBody
  auth: AuthConfig
  settings: RequestSettings
}

export interface CaseMeta {
  pre_operations?: Operation[]
  post_operations?: Operation[]
  response_extract?: ExtractRow[]
  auth?: AuthConfig
  body_type?: BodyType
  form_body?: KvRow[]
  variables?: KvRow[]
  authorization_header?: string
  [key: string]: unknown
}

export interface EditorVariable {
  name: string
  value: string
  scope: string
  scopeLabel: string
}

export interface DataDriveRow {
  enabled: boolean
  values: Record<string, string>
}

export interface BodyStores {
  json: string
  raw: string
  graphql_query: string
  graphql_variables: string
}

export interface ParsedCaseConfig {
  headerRows: KvRow[]
  auth: AuthConfig
  bodyType: BodyType
  formBodyRows: KvRow[]
  bodyStores: BodyStores
  variableRows: KvRow[]
  preOperations: Operation[]
  postOperations: Operation[]
  preScriptStores: ScriptStores
  preScriptLang: string
  postScript: string
  extractRows: ExtractRow[]
  extractSource: ExtractSource | string
  assertions: string
  dataDriveRows: DataDriveRow[]
  meta: CaseMeta
}

export interface SerializeCaseConfigInput {
  headerRows?: KvRow[]
  auth?: AuthConfig
  bodyType?: BodyType
  formBodyRows?: KvRow[]
  bodyStores?: BodyStores
  variableRows?: KvRow[]
  preOperations?: Operation[]
  postOperations?: Operation[]
  dataDriveRows?: DataDriveRow[]
}

export interface UrlSplit {
  baseUrl: string
  path: string
  queryRows: KvRow[]
  pathRows: KvRow[]
}

export interface CurlParseResult {
  name: string
  method: string
  path: string
  request_spec: {
    query: KvRow[]
    path_params: KvRow[]
    headers: KvRow[]
    cookies: KvRow[]
    body: Pick<RequestBody, 'type' | 'raw' | 'form'> & Partial<RequestBody>
    auth: Partial<AuthConfig> & { type: string }
  }
}

export type SchemaFieldType =
  'string' | 'integer' | 'number' | 'boolean' | 'object' | 'array' | 'ref'

export interface SchemaField {
  uid: number
  name: string
  type: SchemaFieldType | string
  description: string
  required: boolean
  refName: string
  extra: Record<string, unknown>
  children: SchemaField[]
}

export type JsonSchemaObject = Record<string, unknown>

export interface RequestSpecHolderForm {
  name?: string | null
  method?: string
  path?: string
  server_name?: string | null
  request_spec: RequestSpec
  description?: string | null
  response_schema_id?: number | null
  contract_strict?: boolean
  assertions?: Schemas['AssertionRow'][]
  extracts?: Schemas['ExtractRow'][]
  pre_scripts?: Schemas['CaseScriptOut'][]
  post_scripts?: Schemas['CaseScriptOut'][]
  pre_processors?: Schemas['ProcessorRow'][]
  post_processors?: Schemas['ProcessorRow'][]
}

export interface EndpointEditorForm {
  method: string
  path: string
  name: string
  server_name?: string | null
  request_spec: RequestSpec
  description?: string | null
  response_schema_id?: number | null
  contract_strict?: boolean
  assertions?: Schemas['AssertionRow'][]
  extracts?: Schemas['ExtractRow'][]
  pre_scripts?: Schemas['CaseScriptOut'][]
  post_scripts?: Schemas['CaseScriptOut'][]
  pre_processors?: Schemas['ProcessorRow'][]
  post_processors?: Schemas['ProcessorRow'][]
}

export interface ApiDocPreviewForm {
  method: string
  path?: string
  name?: string
  description?: string | null
  request_spec?: RequestSpec
}

export type EndpointForm = EndpointEditorForm & { id: number }

export interface ConditionConfig {
  left: string
  operator: string
  right: string
}

export interface LoopConfig {
  mode: string
  count?: number | null
  list_var?: string
  item_var?: string
  index_var?: string
  max_iterations?: number | null
  condition?: ConditionConfig
}

export interface DbExtractRow {
  var_name: string
  column: string
  scope: string
}

export interface DbStepConfig {
  connection_id: number | null
  sql: string
  extracts: DbExtractRow[]
}

export interface IfStepConfig {
  condition: ConditionConfig
}

export interface HttpStepConfig {
  name: string
  method: string
  path: string
  server_name?: string | null
  request_spec: RequestSpec
  assertions: Schemas['AssertionRow'][]
  extracts: Schemas['ExtractRow'][]
}

export type StepEditorConfig =
  IfStepConfig | LoopConfig | DbStepConfig | HttpStepConfig | Record<string, unknown>

/** 场景步骤编辑器工作态（比 API StepOut 更宽松，含 UI 专用字段） */
export interface ScenarioEditorStep {
  type: string
  ref_case_id?: number | null
  ref_scenario_id?: number | null
  wait_ms?: number | null
  config?: StepEditorConfig | null
  name?: string | null
  enabled: boolean
  children?: ScenarioEditorStep[]
  case_name?: string
  endpoint_method?: string
  endpoint_path?: string
  scenario_name?: string
  /** 稳定节点 id：加载时为 `s-N` 字符串，新建为递增数字 */
  _uid?: number | string
  elseChildren?: ScenarioEditorStep[]
  elseEnabled?: boolean
}

export interface ScenarioStepSelection {
  uid: number | string | null
}

export function ensureIfConfig(step: ScenarioEditorStep): IfStepConfig {
  const cfg = step.config
  if (!cfg || typeof cfg !== 'object' || !('condition' in cfg)) {
    step.config = { condition: { left: '', operator: 'eq', right: '' } }
  }
  return step.config as IfStepConfig
}

export function ensureLoopConfig(step: ScenarioEditorStep): LoopConfig {
  const cfg = step.config
  if (!cfg || typeof cfg !== 'object' || !('mode' in cfg)) {
    step.config = {
      mode: 'count',
      count: 1,
      list_var: '',
      item_var: 'item',
      index_var: 'index',
      max_iterations: 10,
      condition: { left: '', operator: 'eq', right: '' },
    }
  }
  return step.config as LoopConfig
}

export function ensureDbConfig(step: ScenarioEditorStep): DbStepConfig {
  const cfg = step.config
  if (!cfg || typeof cfg !== 'object' || !('sql' in cfg)) {
    step.config = { connection_id: null, sql: '', extracts: [] }
  }
  const db = step.config as DbStepConfig
  if (!Array.isArray(db.extracts)) db.extracts = []
  return db
}

export function ensureHttpConfig(step: ScenarioEditorStep): HttpStepConfig {
  const cfg = step.config
  if (!cfg || typeof cfg !== 'object' || !('method' in cfg)) {
    step.config = {
      name: '',
      method: 'GET',
      path: '',
      server_name: null,
      request_spec: emptySpec(),
      assertions: [],
      extracts: [],
    }
  }
  const http = step.config as HttpStepConfig
  if (!http.request_spec) http.request_spec = emptySpec()
  if (!Array.isArray(http.assertions)) http.assertions = []
  if (!Array.isArray(http.extracts)) http.extracts = []
  return http
}

export function ensureStepChildren(step: ScenarioEditorStep): ScenarioEditorStep[] {
  if (!Array.isArray(step.children)) step.children = []
  return step.children
}

export function ensureElseChildren(step: ScenarioEditorStep): ScenarioEditorStep[] {
  if (!Array.isArray(step.elseChildren)) step.elseChildren = []
  return step.elseChildren
}

/** Apifox 请求规格、用例配置、操作编排等 UI 层共享类型 */

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

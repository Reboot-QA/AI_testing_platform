// JSON Schema ↔ 可视化字段树 的双向转换。
import type { JsonSchemaObject, SchemaField, SchemaFieldType } from '@/types/apifox'

export const SCHEMA_TYPES = ['string', 'integer', 'number', 'boolean', 'object', 'array'] as const
export const FIELD_TYPES = [...SCHEMA_TYPES, 'ref'] as const
export const MODEL_REF_PREFIX = '#/models/'

const STRUCT_KEYS = new Set(['type', 'properties', 'items', '$ref', 'description'])

let _uid = 0
function uid(): number {
  return ++_uid
}

export function newField(type: SchemaFieldType = 'string'): SchemaField {
  return {
    uid: uid(),
    name: '',
    type,
    description: '',
    required: false,
    refName: '',
    extra: {},
    children: [],
  }
}

function pickExtra(sub: JsonSchemaObject): Record<string, unknown> {
  const extra: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(sub || {})) {
    if (!STRUCT_KEYS.has(k) && k !== 'required') extra[k] = v
  }
  return extra
}

function toField(name: string, sub: JsonSchemaObject | undefined, required: boolean): SchemaField {
  const s = sub || {}
  if (typeof s.$ref === 'string' && s.$ref.startsWith(MODEL_REF_PREFIX)) {
    return {
      uid: uid(),
      name: name || '',
      type: 'ref',
      refName: s.$ref.slice(MODEL_REF_PREFIX.length),
      description: (s.description as string) || '',
      required,
      extra: pickExtra(s),
      children: [],
    }
  }
  const type = SCHEMA_TYPES.includes(s.type as (typeof SCHEMA_TYPES)[number])
    ? (s.type as SchemaFieldType)
    : 'string'
  const field: SchemaField = {
    uid: uid(),
    name: name || '',
    type,
    description: (s.description as string) || '',
    required,
    refName: '',
    extra: pickExtra(s),
    children: [],
  }
  if (type === 'object') {
    field.children = objectToFields(s)
  } else if (type === 'array') {
    field.children = [toField('', (s.items as JsonSchemaObject) || { type: 'string' }, false)]
  }
  return field
}

function objectToFields(objSchema: JsonSchemaObject): SchemaField[] {
  const props = (objSchema?.properties as Record<string, JsonSchemaObject>) || {}
  const required = (objSchema?.required as string[]) || []
  return Object.entries(props).map(([name, sub]) => toField(name, sub, required.includes(name)))
}

export function schemaToFields(schema: JsonSchemaObject | null | undefined): SchemaField[] {
  const root = schema && typeof schema === 'object' ? schema : {}
  return objectToFields(root)
}

const NUMERIC_KEYS = new Set([
  'minimum',
  'maximum',
  'exclusiveMinimum',
  'exclusiveMaximum',
  'multipleOf',
  'minLength',
  'maxLength',
  'minItems',
  'maxItems',
  'minProperties',
  'maxProperties',
])

function cleanExtra(extra: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(extra || {})) {
    if (v === null || v === undefined) continue
    if (Array.isArray(v) && v.length === 0) continue
    if (NUMERIC_KEYS.has(k)) {
      if (typeof v === 'boolean') {
        out[k] = v
        continue
      }
      if (v === '') continue
      const n = Number(v)
      if (!Number.isNaN(n)) out[k] = n
      continue
    }
    out[k] = v
  }
  return out
}

function fieldToSchema(field: SchemaField): JsonSchemaObject {
  if (field.type === 'ref') {
    const out: JsonSchemaObject = {
      ...cleanExtra(field.extra),
      $ref: MODEL_REF_PREFIX + (field.refName || ''),
    }
    if (field.description) out.description = field.description
    return out
  }
  const out: JsonSchemaObject = { ...cleanExtra(field.extra) }
  if (field.type === 'object') {
    out.type = 'object'
    Object.assign(out, objectFromFields(field.children))
  } else if (field.type === 'array') {
    out.type = 'array'
    out.items = field.children[0] ? fieldToSchema(field.children[0]) : { type: 'string' }
  } else {
    out.type = field.type
  }
  if (field.description) out.description = field.description
  return out
}

function objectFromFields(fields: SchemaField[]): JsonSchemaObject {
  const properties: Record<string, JsonSchemaObject> = {}
  const required: string[] = []
  for (const f of fields || []) {
    if (!f.name) continue
    properties[f.name] = fieldToSchema(f)
    if (f.required) required.push(f.name)
  }
  const out: JsonSchemaObject = { properties }
  if (required.length) out.required = required
  return out
}

export function fieldsToSchema(fields: SchemaField[]): JsonSchemaObject {
  return { type: 'object', ...objectFromFields(fields) }
}

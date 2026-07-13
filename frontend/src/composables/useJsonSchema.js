// JSON Schema ↔ 可视化字段树 的双向转换。
// 字段树：每个字段 { uid, name, type, description, required, children }。
// object 的 children 是其属性字段；array 的 children 是单元素[items 字段]（name 不用）。

export const SCHEMA_TYPES = ['string', 'integer', 'number', 'boolean', 'object', 'array']
// 可视化下拉可选类型（含「引用模型」，映射为 $ref）
export const FIELD_TYPES = [...SCHEMA_TYPES, 'ref']
export const MODEL_REF_PREFIX = '#/models/'

let _uid = 0
function uid() {
  return ++_uid
}

export function newField(type = 'string') {
  return { uid: uid(), name: '', type, description: '', required: false, refName: '', children: [] }
}

function toField(name, sub, required) {
  const s = sub || {}
  // 跨模型引用 {"$ref":"#/models/X"} → ref 字段
  if (typeof s.$ref === 'string' && s.$ref.startsWith(MODEL_REF_PREFIX)) {
    return {
      uid: uid(), name: name || '', type: 'ref', refName: s.$ref.slice(MODEL_REF_PREFIX.length),
      description: s.description || '', required, children: [],
    }
  }
  const type = SCHEMA_TYPES.includes(s.type) ? s.type : 'string'
  const field = {
    uid: uid(), name: name || '', type, description: s.description || '', required, refName: '', children: [],
  }
  if (type === 'object') {
    field.children = objectToFields(s)
  } else if (type === 'array') {
    field.children = [toField('', s.items || { type: 'string' }, false)]
  }
  return field
}

function objectToFields(objSchema) {
  const props = (objSchema && objSchema.properties) || {}
  const required = (objSchema && objSchema.required) || []
  return Object.entries(props).map(([name, sub]) => toField(name, sub, required.includes(name)))
}

export function schemaToFields(schema) {
  const root = schema && typeof schema === 'object' ? schema : {}
  return objectToFields(root)
}

function fieldToSchema(field) {
  if (field.type === 'ref') {
    const out = { $ref: MODEL_REF_PREFIX + (field.refName || '') }
    if (field.description) out.description = field.description
    return out
  }
  const out = {}
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

function objectFromFields(fields) {
  const properties = {}
  const required = []
  for (const f of fields || []) {
    if (!f.name) continue
    properties[f.name] = fieldToSchema(f)
    if (f.required) required.push(f.name)
  }
  const out = { properties }
  if (required.length) out.required = required
  return out
}

export function fieldsToSchema(fields) {
  return { type: 'object', ...objectFromFields(fields) }
}

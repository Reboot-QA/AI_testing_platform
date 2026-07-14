// JSON Schema ↔ 可视化字段树 的双向转换。
// 字段树：每个字段 { uid, name, type, description, required, refName, extra, children }。
// object 的 children 是其属性字段；array 的 children 是单元素[items 字段]（name 不用）。
// extra：结构键(type/properties/items/required/$ref/description)之外的所有关键字（enum/pattern/
// minimum/format/default/example/nullable/未知手写关键字…）原样保留，保证源码↔可视化往返无损。

export const SCHEMA_TYPES = ['string', 'integer', 'number', 'boolean', 'object', 'array']
// 可视化下拉可选类型（含「引用模型」，映射为 $ref）
export const FIELD_TYPES = [...SCHEMA_TYPES, 'ref']
export const MODEL_REF_PREFIX = '#/models/'

// 结构键由字段树结构本身表达，不进 extra
const STRUCT_KEYS = new Set(['type', 'properties', 'items', '$ref', 'description'])

let _uid = 0
function uid() {
  return ++_uid
}

export function newField(type = 'string') {
  return { uid: uid(), name: '', type, description: '', required: false, refName: '', extra: {}, children: [] }
}

// 收集 sub 里的非结构关键字（required 在父级 object 处理，这里也排除）
function pickExtra(sub) {
  const extra = {}
  for (const [k, v] of Object.entries(sub || {})) {
    if (!STRUCT_KEYS.has(k) && k !== 'required') extra[k] = v
  }
  return extra
}

function toField(name, sub, required) {
  const s = sub || {}
  // 跨模型引用 {"$ref":"#/models/X"} → ref 字段
  if (typeof s.$ref === 'string' && s.$ref.startsWith(MODEL_REF_PREFIX)) {
    return {
      uid: uid(), name: name || '', type: 'ref', refName: s.$ref.slice(MODEL_REF_PREFIX.length),
      description: s.description || '', required, extra: pickExtra(s), children: [],
    }
  }
  const type = SCHEMA_TYPES.includes(s.type) ? s.type : 'string'
  const field = {
    uid: uid(), name: name || '', type, description: s.description || '', required,
    refName: '', extra: pickExtra(s), children: [],
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

// 清洗 extra：丢弃空值(null/undefined/''/空数组)，数字型约束转数字
const NUMERIC_KEYS = new Set([
  'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf',
  'minLength', 'maxLength', 'minItems', 'maxItems', 'minProperties', 'maxProperties',
])
function cleanExtra(extra) {
  const out = {}
  for (const [k, v] of Object.entries(extra || {})) {
    if (v === null || v === undefined || v === '') continue
    if (Array.isArray(v) && v.length === 0) continue
    if (NUMERIC_KEYS.has(k)) {
      const n = Number(v)
      if (!Number.isNaN(n)) out[k] = n
      continue
    }
    out[k] = v
  }
  return out
}

function fieldToSchema(field) {
  if (field.type === 'ref') {
    const out = { ...cleanExtra(field.extra), $ref: MODEL_REF_PREFIX + (field.refName || '') }
    if (field.description) out.description = field.description
    return out
  }
  const out = { ...cleanExtra(field.extra) } // 先铺约束/未知键，结构键随后覆盖
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

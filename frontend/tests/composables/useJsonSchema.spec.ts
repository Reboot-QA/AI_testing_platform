import { describe, expect, it } from 'vitest'
import type { JsonSchemaObject, SchemaField } from '@/types/apifox'
import {
  FIELD_TYPES,
  SCHEMA_TYPES,
  fieldsToSchema,
  newField,
  schemaToFields,
} from '@/composables/useJsonSchema'

describe('newField', () => {
  it('默认 string，uid 递增', () => {
    const a = newField()
    const b = newField('integer')
    expect(a).toMatchObject({
      name: '',
      type: 'string',
      required: false,
      children: [],
    })
    expect(b.type).toBe('integer')
    expect(b.uid).toBeGreaterThan(a.uid)
  })
})

describe('schemaToFields / fieldsToSchema', () => {
  it('空/非法 schema 得到空字段', () => {
    expect(schemaToFields(null)).toEqual([])
    expect(schemaToFields(undefined)).toEqual([])
  })

  it('解析 object / array / $ref，并保留 required 与 extra', () => {
    const schema: JsonSchemaObject = {
      type: 'object',
      required: ['id'],
      properties: {
        id: { type: 'integer', minimum: 1, description: '主键' },
        tags: {
          type: 'array',
          items: { type: 'string' },
        },
        user: { $ref: '#/models/User', description: '用户' },
        weird: { type: 'unknown-type' as 'string' },
      },
    }
    const fields = schemaToFields(schema)
    expect(fields.map((f) => f.name)).toEqual(['id', 'tags', 'user', 'weird'])
    expect(fields[0]).toMatchObject({
      type: 'integer',
      required: true,
      description: '主键',
      extra: { minimum: 1 },
    })
    expect(fields[1]!.type).toBe('array')
    expect(fields[1]!.children[0]!.type).toBe('string')
    expect(fields[2]).toMatchObject({ type: 'ref', refName: 'User', description: '用户' })
    expect(fields[3]!.type).toBe('string')
  })

  it('字段树回写 schema（跳过无名、清理空 extra）', () => {
    const fields: SchemaField[] = [
      {
        ...newField('string'),
        name: 'title',
        required: true,
        description: '标题',
        extra: { minLength: '2', emptyArr: [], skip: null },
      },
      {
        ...newField('object'),
        name: 'meta',
        children: [{ ...newField('boolean'), name: 'draft', required: false }],
      },
      {
        ...newField('array'),
        name: 'ids',
        children: [{ ...newField('integer'), name: '' }],
      },
      {
        ...newField('ref'),
        name: 'owner',
        refName: 'User',
        description: '负责人',
      },
      { ...newField('string'), name: '' },
    ]
    const schema = fieldsToSchema(fields)
    expect(schema.type).toBe('object')
    expect(schema.required).toEqual(['title'])
    expect(schema.properties).toMatchObject({
      title: { type: 'string', description: '标题', minLength: 2 },
      meta: {
        type: 'object',
        properties: { draft: { type: 'boolean' } },
      },
      ids: { type: 'array', items: { type: 'integer' } },
      owner: { $ref: '#/models/User', description: '负责人' },
    })
    expect(Object.keys(schema.properties || {})).not.toContain('')
  })

  it('SCHEMA_TYPES / FIELD_TYPES 含基础类型与 ref', () => {
    expect(SCHEMA_TYPES).toContain('object')
    expect(FIELD_TYPES).toContain('ref')
  })
})

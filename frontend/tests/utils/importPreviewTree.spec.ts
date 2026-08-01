import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/types'
import type { ImportPreviewNode } from '@/types/apifox'
import {
  ROOT_KEY,
  GROUP_KEY,
  buildImportPreviewTree,
  buildFolderOptions,
  collectEndpointKeys,
  filterPreviewNode,
  pickCheckedEndpointKeys,
} from '@/utils/importPreviewTree'

describe('buildImportPreviewTree', () => {
  it('无 tag 的接口直接挂在接口分组下', () => {
    const preview: Schemas['ImportPreviewOut'] = {
      title: 'OpenAPI',
      total: 2,
      exists_count: 0,
      changed_count: 0,
      schemas_total: 0,
      schemas_new: 0,
      folders: [
        {
          name: '',
          endpoints: [
            {
              key: 'GET /ping',
              name: 'ping',
              method: 'GET',
              path: '/ping',
              folder: '',
              exists: false,
              changed: false,
            },
          ],
        },
        {
          name: 'user',
          endpoints: [
            {
              key: 'POST /users',
              name: 'create',
              method: 'POST',
              path: '/users',
              folder: 'user',
              exists: true,
              changed: true,
            },
          ],
        },
      ],
    }
    const tree = buildImportPreviewTree(preview)
    expect(tree[0]!.key).toBe(ROOT_KEY)
    expect(tree[0]!.children![0]!.key).toBe(GROUP_KEY)
    const children = tree[0]!.children![0]!.children!
    expect(children[0]).toMatchObject({ type: 'endpoint', key: 'GET /ping' })
    expect(children[1]).toMatchObject({
      type: 'folder',
      label: 'user',
      count: 1,
    })
    expect(children[1]!.children![0]!.key).toBe('POST /users')
  })
})

describe('collectEndpointKeys / pickCheckedEndpointKeys', () => {
  const nodes: ImportPreviewNode[] = [
    {
      key: ROOT_KEY,
      label: 'root',
      type: 'root',
      children: [
        {
          key: GROUP_KEY,
          label: '接口',
          type: 'group',
          children: [
            {
              key: '#folder#a',
              label: 'a',
              type: 'folder',
              children: [
                { key: 'GET /a', label: 'a', type: 'endpoint', method: 'GET', path: '/a' },
                { key: 'POST /a', label: 'a2', type: 'endpoint', method: 'POST', path: '/a' },
              ],
            },
            { key: 'GET /b', label: 'b', type: 'endpoint', method: 'GET', path: '/b' },
          ],
        },
      ],
    },
  ]

  it('收集全部接口 key', () => {
    expect(collectEndpointKeys(nodes)).toEqual(['GET /a', 'POST /a', 'GET /b'])
  })

  it('勾中父节点向下传播到未展开的后代', () => {
    expect(pickCheckedEndpointKeys(nodes, new Set(['#folder#a']))).toEqual(['GET /a', 'POST /a'])
    expect(pickCheckedEndpointKeys(nodes, new Set(['GET /b']))).toEqual(['GET /b'])
    expect(pickCheckedEndpointKeys(nodes, new Set())).toEqual([])
  })
})

describe('filterPreviewNode', () => {
  const ep: ImportPreviewNode = {
    key: 'GET /Users',
    label: 'List Users',
    type: 'endpoint',
    method: 'GET',
    path: '/Users',
  }

  it('空关键字恒 true', () => {
    expect(filterPreviewNode('', ep)).toBe(true)
    expect(filterPreviewNode('  ', ep)).toBe(true)
  })

  it('匹配 label / path / method（大小写不敏感）', () => {
    expect(filterPreviewNode('list', ep)).toBe(true)
    expect(filterPreviewNode('/users', ep)).toBe(true)
    expect(filterPreviewNode('get', ep)).toBe(true)
    expect(filterPreviewNode('delete', ep)).toBe(false)
  })
})

describe('buildFolderOptions', () => {
  it('按 parent_id 建树并 prune 空 children', () => {
    const folders: Schemas['FolderOut'][] = [
      { id: 1, project_id: 1, parent_id: null, name: 'root', sort_order: 0 },
      { id: 2, project_id: 1, parent_id: 1, name: 'child', sort_order: 0 },
      { id: 3, project_id: 1, parent_id: null, name: 'orphan', sort_order: 1 },
    ]
    const roots = buildFolderOptions(folders)
    expect(roots).toHaveLength(2)
    expect(roots[0]).toMatchObject({ value: 1, label: 'root' })
    expect(roots[0]!.children).toEqual([{ value: 2, label: 'child' }])
    expect(roots[1]).toEqual({ value: 3, label: 'orphan' })
  })

  it('空列表返回空', () => {
    expect(buildFolderOptions([])).toEqual([])
  })
})

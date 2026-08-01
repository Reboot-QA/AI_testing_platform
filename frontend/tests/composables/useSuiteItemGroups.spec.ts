import { describe, expect, it } from 'vitest'
import type { Schemas } from '@/api/types'
import type { SuiteEditorItem } from '@/types/apifox'
import {
  buildSuiteItemGroups,
  flattenSuiteItemGroups,
  sameOrder,
} from '@/composables/useSuiteItemGroups'

function caseItem(
  partial: Partial<SuiteEditorItem> & Pick<SuiteEditorItem, 'target_id' | '_uid'>,
): SuiteEditorItem {
  return {
    target_type: 'case',
    enabled: true,
    target_name: '',
    endpoint_method: 'GET',
    endpoint_path: '/x',
    ...partial,
  }
}

function scenarioItem(
  partial: Partial<SuiteEditorItem> & Pick<SuiteEditorItem, 'target_id' | '_uid'>,
): SuiteEditorItem {
  return {
    target_type: 'scenario',
    enabled: true,
    target_name: '',
    endpoint_method: '',
    endpoint_path: '',
    ...partial,
  }
}

describe('buildSuiteItemGroups', () => {
  it('空列表返回空', () => {
    expect(buildSuiteItemGroups([])).toEqual([])
  })

  it('按接口聚合用例，场景组恒排最后；组序取首次出现', () => {
    const items: SuiteEditorItem[] = [
      caseItem({
        target_id: 1,
        _uid: 'a',
        endpoint_method: 'GET',
        endpoint_path: '/users',
      }),
      caseItem({
        target_id: 2,
        _uid: 'b',
        endpoint_method: 'POST',
        endpoint_path: '/users',
      }),
      caseItem({
        target_id: 3,
        _uid: 'c',
        endpoint_method: 'GET',
        endpoint_path: '/users',
      }),
      scenarioItem({ target_id: 9, _uid: 's1', target_name: '登录流' }),
      scenarioItem({ target_id: 10, _uid: 's2' }),
    ]
    const briefs: Schemas['ProjectCaseBrief'][] = [
      {
        id: 1,
        name: 'list',
        endpoint_id: 1,
        endpoint_name: '用户列表',
        endpoint_method: 'GET',
      },
      {
        id: 2,
        name: 'create',
        endpoint_id: 2,
        endpoint_name: '创建用户',
        endpoint_method: 'POST',
      },
    ]
    const groups = buildSuiteItemGroups(items, briefs)
    expect(groups.map((g) => g.key)).toEqual(['case:GET /users', 'case:POST /users', 'scenario'])
    expect(groups[0]).toMatchObject({
      kind: 'case',
      name: '用户列表',
      method: 'GET',
      path: '/users',
    })
    expect(groups[0]!.items.map((i) => i._uid)).toEqual(['a', 'c'])
    expect(groups[1]!.name).toBe('创建用户')
    expect(groups[2]).toMatchObject({ kind: 'scenario', key: 'scenario' })
    expect(groups[2]!.items).toHaveLength(2)
  })

  it('查不到用例名时退化为路径或「未知接口」', () => {
    const withPath = buildSuiteItemGroups([
      caseItem({ target_id: 1, _uid: 'a', endpoint_path: '/gone' }),
    ])
    expect(withPath[0]!.name).toBe('/gone')

    const noPath = buildSuiteItemGroups([caseItem({ target_id: 1, _uid: 'a', endpoint_path: '' })])
    expect(noPath[0]!.name).toBe('未知接口')
  })
})

describe('flattenSuiteItemGroups / sameOrder', () => {
  it('展开保持组内顺序', () => {
    const items = [
      caseItem({ target_id: 1, _uid: 'a', endpoint_path: '/a' }),
      caseItem({ target_id: 2, _uid: 'b', endpoint_path: '/b' }),
    ]
    const groups = buildSuiteItemGroups(items)
    expect(flattenSuiteItemGroups(groups)).toEqual(items)
  })

  it('sameOrder 按引用比较', () => {
    const a = caseItem({ target_id: 1, _uid: 'a' })
    const b = caseItem({ target_id: 2, _uid: 'b' })
    expect(sameOrder([a, b], [a, b])).toBe(true)
    expect(sameOrder([a, b], [b, a])).toBe(false)
    expect(sameOrder([a], [a, b])).toBe(false)
    expect(sameOrder([a], [{ ...a }])).toBe(false)
  })
})

import { describe, expect, it } from 'vitest'
import {
  buildScheduleTargetTree,
  keyToTargetId,
  targetToKey,
  type ScheduleTargetSource,
} from '@/composables/useScheduleTargetTree'

const emptySrc: ScheduleTargetSource = {
  folders: [],
  endpoints: [],
  cases: [],
  scenarioFolders: [],
  scenarios: [],
  suites: [],
}

describe('targetToKey / keyToTargetId', () => {
  it('按类型加前缀；空 id 返回 null', () => {
    expect(targetToKey('case', 12)).toBe('c-12')
    expect(targetToKey('scenario', 3)).toBe('s-3')
    expect(targetToKey('suite', 7)).toBe('su-7')
    expect(targetToKey('case', null)).toBeNull()
  })

  it('从 key 解析 target_id；非法返回 null', () => {
    expect(keyToTargetId('c-12')).toBe(12)
    expect(keyToTargetId('su-7')).toBe(7)
    expect(keyToTargetId(null)).toBeNull()
    expect(keyToTargetId('')).toBeNull()
    expect(keyToTargetId('c-x')).toBeNull()
  })
})

describe('buildScheduleTargetTree', () => {
  it('suite：扁平可点叶子', () => {
    const tree = buildScheduleTargetTree('suite', {
      ...emptySrc,
      suites: [
        { id: 1, name: '回归', item_count: 0, sort_order: 0 },
        { id: 2, name: '冒烟', item_count: 0, sort_order: 1 },
      ],
    })
    expect(tree).toEqual([
      {
        key: 'su-1',
        id: 1,
        type: 'suite',
        label: '回归',
        shortLabel: '回归',
        disabled: false,
      },
      {
        key: 'su-2',
        id: 2,
        type: 'suite',
        label: '冒烟',
        shortLabel: '冒烟',
        disabled: false,
      },
    ])
  })

  it('scenario：目录可点场景叶子，父节点 disabled', () => {
    const tree = buildScheduleTargetTree('scenario', {
      ...emptySrc,
      scenarioFolders: [{ id: 10, name: '登录', scenario_count: 1 }],
      scenarios: [
        {
          id: 5,
          name: '成功登录',
          priority: 'medium',
          folder_id: 10,
          step_count: 1,
          sort_order: 0,
        },
      ],
    })
    expect(tree.length).toBeGreaterThan(0)
    const folder = tree.find((n) => n.type === 'scenario-folder' || n.label === '登录')
    expect(folder?.disabled).toBe(true)
    const leaf = tree.flatMap((n) => [n, ...(n.children ?? [])]).find((n) => n.type === 'scenario')
    expect(leaf).toMatchObject({
      key: 's-5',
      shortLabel: '成功登录',
      disabled: false,
    })
  })

  it('case：用例叶子带长标签，非叶子 disabled', () => {
    const tree = buildScheduleTargetTree('case', {
      ...emptySrc,
      folders: [{ id: 1, project_id: 1, parent_id: null, name: 'user', sort_order: 0 }],
      endpoints: [
        {
          id: 2,
          name: '列表',
          method: 'GET',
          path: '/users',
          folder_id: 1,
          sort_order: 0,
          cases_stale: false,
        },
      ],
      cases: [
        {
          id: 9,
          name: '正常列表',
          endpoint_id: 2,
          endpoint_name: '列表',
          endpoint_method: 'GET',
        },
      ],
    })
    const leaves = tree
      .flatMap(function walk(n): typeof tree {
        return [n, ...(n.children ?? []).flatMap(walk)]
      })
      .filter((n) => n.type === 'case')
    expect(leaves).toHaveLength(1)
    expect(leaves[0]).toMatchObject({
      key: 'c-9',
      shortLabel: '正常列表',
      disabled: false,
    })
    expect(leaves[0]!.label).toContain('[GET]')
    expect(leaves[0]!.label).toContain('/users')
    expect(leaves[0]!.label).toContain('正常列表')
  })
})

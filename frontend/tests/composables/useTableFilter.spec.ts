import { describe, expect, it } from 'vitest'
import { ref } from 'vue'
import { useTableFilter } from '@/composables/useTableFilter'

interface Row {
  name: string
  status: string
  note?: string | null
}

describe('useTableFilter', () => {
  it('无关键字时返回全部（可叠加 predicate）', () => {
    const source = ref<Row[]>([
      { name: 'Alpha', status: 'open' },
      { name: 'Beta', status: 'closed' },
    ])
    const { keyword, filtered } = useTableFilter(source, {
      keywordFields: (r) => [r.name],
      predicate: (r) => r.status === 'open',
    })
    expect(keyword.value).toBe('')
    expect(filtered.value.map((r) => r.name)).toEqual(['Alpha'])
  })

  it('关键字大小写不敏感，忽略空字段', () => {
    const source = ref<Row[]>([
      { name: 'Login API', status: 'open', note: null },
      { name: 'Logout', status: 'open', note: 'auth' },
      { name: 'Health', status: 'open' },
    ])
    const { keyword, filtered } = useTableFilter(source, {
      keywordFields: (r) => [r.name, r.note],
    })
    keyword.value = '  AUTH  '
    expect(filtered.value.map((r) => r.name)).toEqual(['Logout'])
  })

  it('source 变更后 filtered 跟随更新', () => {
    const source = ref<Row[]>([{ name: 'A', status: 'open' }])
    const { filtered } = useTableFilter(source, {
      keywordFields: (r) => [r.name],
    })
    expect(filtered.value).toHaveLength(1)
    source.value = [
      { name: 'A', status: 'open' },
      { name: 'B', status: 'open' },
    ]
    expect(filtered.value).toHaveLength(2)
  })
})

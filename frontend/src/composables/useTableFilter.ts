import { computed, ref, type ComputedRef, type Ref } from 'vue'

/**
 * 全量返回类列表的客户端检索（统一范式）：关键字模糊匹配 + 可选枚举/等值谓词。
 *
 * 适用于「后端一次性返回数组、前端无分页」的列表（回收站、场景、套件、用例、Schema、脚本、
 * 数据集、定时任务…）。**分页类列表**（AI 任务、测试报告、工作台）请改走后端查询参数
 * `keyword` / `status` / `date_from` / `date_to`，勿用本组合式（否则只过滤当前页）。
 */
export function useTableFilter<T>(
  source: Ref<readonly T[]>,
  options: {
    /** 每行参与关键字模糊匹配的文本片段（大小写不敏感、忽略空值） */
    keywordFields: (row: T) => Array<string | null | undefined>
    /** 额外的枚举/等值过滤（返回 false 即排除该行）；内部读取响应式 ref 会随之更新 */
    predicate?: (row: T) => boolean
  },
): {
  keyword: Ref<string>
  filtered: ComputedRef<T[]>
} {
  const keyword = ref('')

  const filtered = computed<T[]>(() => {
    const kw = keyword.value.trim().toLowerCase()
    return source.value.filter((row) => {
      if (options.predicate && !options.predicate(row)) return false
      if (!kw) return true
      return options.keywordFields(row).some((v) => (v ?? '').toLowerCase().includes(kw))
    })
  })

  return { keyword, filtered }
}

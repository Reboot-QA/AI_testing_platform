// ElMessageBox.prompt 的统一输入校验：弹窗输入框无法设 maxlength，只能靠 inputValidator。
import { TITLE_MAX_LEN } from '@/constants/limits'

/**
 * 名称类 prompt 的统一校验选项（非空 + 长度上限）。
 * 用法：`ElMessageBox.prompt('接口名称', '添加接口', { ...nameInputOptions() })`
 */
export function nameInputOptions(maxLen: number = TITLE_MAX_LEN) {
  return {
    inputValidator: (value: string): boolean | string => {
      const v = (value ?? '').trim()
      if (!v) return '不能为空'
      if (v.length > maxLen) return `不能超过 ${maxLen} 个字符（当前 ${v.length}）`
      return true
    },
  }
}

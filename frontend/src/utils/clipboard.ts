/**
 * 复制文本到剪贴板。
 *
 * `navigator.clipboard` 仅在安全上下文（HTTPS / localhost）可用；平台部署在 http 时它是
 * undefined，直接调用会抛错、复制"无效"（Confluence 7/23-#9）。这里优先用它，不可用或
 * 失败时回退到临时 textarea + `execCommand('copy')`，保证 http 环境也能复制。
 */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    // 安全上下文写入失败（如权限被拒）也落到下面的回退
  }
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.position = 'fixed'
    ta.style.top = '-9999px'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.focus()
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch {
    return false
  }
}

// 解析 cURL 命令为请求配置（覆盖浏览器/Apifox 常见复制格式）。
// 返回 { name, method, path, request_spec:{query,path_params,headers,cookies,body,auth} } 或 null。

// 简易 shell 分词：处理单/双引号、行尾续行反斜杠、$'...' 前缀
function tokenize(cmd) {
  const s = cmd.replace(/\\\r?\n/g, ' ').trim()
  const tokens = []
  let i = 0
  while (i < s.length) {
    while (i < s.length && /\s/.test(s[i])) i++
    if (i >= s.length) break
    let tok = ''
    while (i < s.length && !/\s/.test(s[i])) {
      const ch = s[i]
      if (ch === "'" || ch === '"') {
        const quote = ch
        i++
        while (i < s.length && s[i] !== quote) {
          if (s[i] === '\\' && quote === '"' && i + 1 < s.length) {
            tok += s[i + 1]
            i += 2
          } else {
            tok += s[i]
            i++
          }
        }
        i++ // 跳过闭合引号
      } else if (ch === '\\' && i + 1 < s.length) {
        tok += s[i + 1]
        i += 2
      } else {
        tok += ch
        i++
      }
    }
    tokens.push(tok)
  }
  return tokens
}

function kvRow(key, value) {
  return { key, value, enabled: true }
}

// URL 判定：含协议、或形如 host.tld[/:?]、或 localhost——避免把未识别 flag 的值(如 --max-time 30 的 30)误当 URL
function looksLikeUrl(t) {
  return /:\/\//.test(t) || /^[\w.-]+\.[a-z]{2,}([:/?]|$)/i.test(t) || /^localhost([:/]|$)/i.test(t)
}

export function parseCurl(raw) {
  if (!raw || !/^\s*curl\b/i.test(raw)) return null
  const toks = tokenize(raw)
  let url = ''
  let method = ''
  const headers = []
  let body = ''
  let auth = null

  for (let i = 0; i < toks.length; i++) {
    const t = toks[i]
    if (t === 'curl') continue
    if (t === '-X' || t === '--request') {
      method = (toks[++i] || '').toUpperCase()
    } else if (t === '-H' || t === '--header') {
      const h = toks[++i] || ''
      const idx = h.indexOf(':')
      if (idx > 0) headers.push(kvRow(h.slice(0, idx).trim(), h.slice(idx + 1).trim()))
    } else if (t === '-d' || t === '--data' || t === '--data-raw' || t === '--data-binary' || t === '--data-ascii') {
      body = toks[++i] || ''
    } else if (t === '-u' || t === '--user') {
      const cred = toks[++i] || ''
      const ci = cred.indexOf(':')
      auth = { type: 'basic', username: ci >= 0 ? cred.slice(0, ci) : cred, password: ci >= 0 ? cred.slice(ci + 1) : '' }
    } else if (t === '--url') {
      url = toks[++i] || ''
    } else if (!t.startsWith('-') && !url && looksLikeUrl(t)) {
      url = t
    }
    // 其它 flag（-i/-s/-k/--compressed 等）忽略
  }

  if (!url) return null
  if (!method) method = body ? 'POST' : 'GET'

  // body 类型：Content-Type 含 json 或内容像 JSON → json，否则 raw
  const ctHeader = headers.find((h) => h.key.toLowerCase() === 'content-type')
  const isJson = (ctHeader && /json/i.test(ctHeader.value)) || /^\s*[[{]/.test(body)
  const bodySpec = body
    ? { type: isJson ? 'json' : 'raw', raw: body, form: [] }
    : { type: 'none', raw: '', form: [] }

  return {
    name: `${method} ${url}`.slice(0, 60),
    method,
    path: url,
    request_spec: {
      query: [],
      path_params: [],
      headers,
      cookies: [],
      body: bodySpec,
      auth: auth || { type: 'none' },
    },
  }
}

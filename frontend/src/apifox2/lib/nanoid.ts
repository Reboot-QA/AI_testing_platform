// 轻量 nanoid 实现，替代 nanoid 依赖（apifox2 内部使用，语义与 nanoid(size) 一致）。
const urlAlphabet = 'useandom-26T198340PX75pxJACKVERYMINDBUSHWOLF_GQZbfghjklqvwyzrict'

export function nanoid(size = 21): string {
  let id = ''
  const cryptoObj = typeof crypto !== 'undefined' ? crypto : undefined
  if (cryptoObj?.getRandomValues) {
    const bytes = cryptoObj.getRandomValues(new Uint8Array(size))
    for (let i = 0; i < size; i++) {
      id += urlAlphabet[bytes[i] & 63]
    }
    return id
  }
  for (let i = 0; i < size; i++) {
    id += urlAlphabet[Math.floor(Math.random() * urlAlphabet.length)]
  }
  return id
}

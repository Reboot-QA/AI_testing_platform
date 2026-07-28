/**
 * 字段长度上限（与后端 app/constants/limits.py 对齐，单一事实来源在后端）。
 *
 * 标题（name/title 等展示名）≤ 100，描述（description）≤ 500；
 * apifox 各标题/描述输入框据此设 maxlength，超限无法输入，呼应后端 422 校验。
 */

/** 标题/名称上限（apifox 主实体展示名 name/title） */
export const TITLE_MAX_LEN = 100

/** 描述上限（apifox 各实体 description） */
export const DESC_MAX_LEN = 500

/** 数据模型(Schema)名称上限：按测试要求收窄到 50（区别于通用标题 100） */
export const MODEL_NAME_MAX_LEN = 50

/**
 * 以下为前端侧输入防护上限：后端对应字段多为 Text/无长度校验，
 * 这里只拦手输与粘贴，避免用户填入超长内容，不构成后端契约。
 */

/** URL 类（前置 URL、导入地址等，对齐 base_url 的 String(500)） */
export const URL_MAX_LEN = 500

/** 键名类（变量名、参数 key、请求头名等） */
export const KEY_MAX_LEN = 100

/** 值类（变量值、请求头值、断言期望值等短值） */
export const VALUE_MAX_LEN = 2000

/** 凭据类（密码、token、密钥，需容纳 JWT / PAT） */
export const SECRET_MAX_LEN = 500

/** 搜索关键字 */
export const SEARCH_MAX_LEN = 100

/** 长文本（用例步骤、预期结果、备注等多行内容） */
export const LONG_TEXT_MAX_LEN = 2000

/**
 * 粘贴类大文本（cURL 报文、需求正文、AI 输入等）。
 * 这类内容天然可能上万字，若按 LONG_TEXT_MAX_LEN 截断会直接废掉功能，故单列一档。
 */
export const PASTE_MAX_LEN = 50000

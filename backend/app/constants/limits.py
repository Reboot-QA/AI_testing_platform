"""字段长度上限常量（单一事实来源，前端 src/config/limits.ts 与之对齐）。

标题（name/title 等展示名）与描述（description）的长度上限统一在此定义，
apifox 各写入 schema（Create/Update）引用，避免 100/500 魔数散落。
"""

# 标题/名称上限（apifox 主实体展示名 name/title）
TITLE_MAX_LEN = 100

# 描述上限（apifox 各实体 description，DB 仍为 Text，仅入参校验）
DESC_MAX_LEN = 500

# 数据模型(Schema)名称上限：按测试要求收窄到 50（区别于通用标题 100）
MODEL_NAME_MAX_LEN = 50

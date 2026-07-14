"""Apifox v2 · 业务异常。

router 按类型转 HTTP 状态码：ConflictError→409（乐观锁冲突），ValueError→400。
"""


class ConflictError(Exception):
    """乐观锁保存冲突：客户端期望版本 ≠ 当前版本（他人已先保存）。

    携带当前版本供前端提示/重载。用于多人协同并发编辑的 last-write-wins 防护。
    """

    def __init__(self, current_version: int, message: str = "内容已被他人修改，请刷新加载最新后再保存"):
        self.current_version = current_version
        self.message = message
        super().__init__(message)

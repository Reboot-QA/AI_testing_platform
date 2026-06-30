from datetime import datetime, timedelta


def now_local() -> datetime:
    """用户可见时间与调度统一使用服务器本地时间（无时区标记的 naive datetime）。"""
    return datetime.now().replace(microsecond=0)


def local_utc_offset() -> timedelta:
    return datetime.now().astimezone().utcoffset() or timedelta(0)


def utc_naive_to_local(dt: datetime) -> datetime:
    """将历史上以 UTC 写入的 naive datetime 转为本地 naive datetime。"""
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None, microsecond=0)
    offset = local_utc_offset()
    if offset == timedelta(0):
        return dt.replace(microsecond=0)
    return (dt + offset).replace(microsecond=0)

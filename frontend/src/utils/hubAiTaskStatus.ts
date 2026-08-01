export function hubStatusText(s: string): string {
  return (
    {
      pending: '排队中',
      running: '生成中',
      succeeded: '成功',
      partial: '部分成功',
      failed: '失败',
      canceled: '已取消',
    }[s] || s
  )
}

export function hubStatusType(s: string): '' | 'success' | 'warning' | 'info' | 'danger' | 'primary' {
  return (
    ({
      succeeded: 'success',
      partial: 'warning',
      failed: 'danger',
      running: 'primary',
      pending: 'warning',
      canceled: 'info',
    })[s] || 'info'
  ) as '' | 'success' | 'warning' | 'info' | 'danger' | 'primary'
}

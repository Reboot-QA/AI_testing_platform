// 运行记录展示的纯格式化函数（测试报告 / 接口报告 tab 共用）
export const statusLabel = (s) => ({ running: '执行中', passed: '通过', failed: '失败' }[s] || s)
export const statusTag = (s) => ({ running: 'warning', passed: 'success', failed: 'danger' }[s] || 'info')
export const formatTime = (v) => (v ? new Date(v).toLocaleString('zh-CN') : '-')

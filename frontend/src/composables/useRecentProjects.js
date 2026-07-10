// 「最近访问」项目记录：存浏览器本地（零后端，个人便捷功能）
const STORAGE_KEY = 'apifox:recent-projects'
const MAX_RECENT = 8

function read() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const list = raw ? JSON.parse(raw) : []
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function write(list) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
  } catch {
    // 隐私模式/配额满：静默降级，最近访问非关键功能
  }
}

export function useRecentProjects() {
  // 进入项目时调用：置顶、去重、限长，时间戳用于排序与展示
  function record(project) {
    if (!project?.id) return
    const rest = read().filter((r) => r.id !== project.id)
    write([{ id: project.id, at: Date.now() }, ...rest].slice(0, MAX_RECENT))
  }

  // 返回按访问时间倒序的记录（{id, at}）；调用方自行与现存项目对齐
  function list() {
    return read()
  }

  return { record, list }
}

const TYPE_ORDER = ['functional', 'api', 'performance', 'security']
const PRIORITY_ORDER = ['P0', 'P1', 'P2', 'P3']

export const TYPE_LABELS = {
  functional: '功能',
  api: '接口',
  performance: '性能',
  security: '安全',
}

export const STATUS_LABELS = {
  draft: '草稿',
  approved: '已评审',
  closed: '已关闭',
}

export const SOURCE_LABELS = {
  manual: '手动',
  ai_document: '文档解析',
}

function sortByOrder(values, order) {
  return [...values].sort((a, b) => {
    const ai = order.indexOf(a)
    const bi = order.indexOf(b)
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
  })
}

function makeNode(id, label, kind, extra = {}) {
  return { id, label, kind, children: [], ...extra }
}

function buildTypePriorityTree(items) {
  const typeGroups = new Map()
  for (const req of items) {
    const typeKey = req.req_type || 'functional'
    if (!typeGroups.has(typeKey)) typeGroups.set(typeKey, [])
    typeGroups.get(typeKey).push(req)
  }

  const typeNodes = []
  for (const typeKey of sortByOrder([...typeGroups.keys()], TYPE_ORDER)) {
    const typeItems = typeGroups.get(typeKey) || []
    const priorityGroups = new Map()
    for (const req of typeItems) {
      const priority = req.priority || 'P2'
      if (!priorityGroups.has(priority)) priorityGroups.set(priority, [])
      priorityGroups.get(priority).push(req)
    }

    const priorityNodes = []
    for (const priority of sortByOrder([...priorityGroups.keys()], PRIORITY_ORDER)) {
      const reqs = (priorityGroups.get(priority) || []).sort((a, b) => b.id - a.id)
      priorityNodes.push(
        makeNode(`priority-${typeKey}-${priority}`, `${priority}（${reqs.length}）`, 'priority', {
          meta: { typeKey, priority },
          children: reqs.map((req) =>
            makeNode(`req-${req.id}`, req.title, 'requirement', {
              requirement: req,
              meta: {
                id: req.id,
                priority: req.priority,
                status: req.status,
                source: req.source,
                req_type: req.req_type,
                testcase_count: req.testcase_count,
              },
            })
          ),
        })
      )
    }

    typeNodes.push(
      makeNode(`type-${typeKey}`, `${TYPE_LABELS[typeKey] || typeKey}（${typeItems.length}）`, 'type', {
        meta: { typeKey },
        children: priorityNodes,
      })
    )
  }
  return typeNodes
}

export function buildRequirementMindTree(requirements, { projectName, isAllProjects }) {
  const rootLabel = isAllProjects ? '需求全景' : projectName || '项目需求'
  const root = makeNode('root', rootLabel, 'root', {
    meta: { total: requirements.length },
  })

  if (!requirements.length) {
    root.children = [makeNode('empty', '暂无需求点', 'empty')]
    return root
  }

  if (isAllProjects) {
    const projectGroups = new Map()
    for (const req of requirements) {
      const key = req.project_id
      if (!projectGroups.has(key)) {
        projectGroups.set(key, { name: req.project_name || `项目 ${key}`, items: [] })
      }
      projectGroups.get(key).items.push(req)
    }

    root.children = [...projectGroups.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([pid, group]) =>
        makeNode(`project-${pid}`, `${group.name}（${group.items.length}）`, 'project', {
          meta: { projectId: pid, projectName: group.name },
          children: buildTypePriorityTree(group.items),
        })
      )
    return root
  }

  root.children = buildTypePriorityTree(requirements)
  return root
}

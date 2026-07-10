<template>
  <el-card class="project-card" shadow="hover" @click="$emit('enter', project.id)">
    <div class="card-title">{{ project.name }}</div>
    <div class="card-desc">{{ project.description || '暂无描述' }}</div>
    <div class="card-meta">
      <el-tag size="small" type="info">需求 {{ project.requirement_count ?? 0 }}</el-tag>
      <el-tag size="small" type="info">用例 {{ project.testcase_count ?? 0 }}</el-tag>
    </div>
    <div class="card-foot">
      <span>{{ project.owner_name || '-' }}</span>
      <span>{{ footText }}</span>
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  project: { type: Object, required: true },
  // 最近访问卡片传访问时间戳，展示「x 前」而非创建日期
  visitedAt: { type: Number, default: null },
})
defineEmits(['enter'])

function relativeTime(ts) {
  const diff = Date.now() - ts
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour} 小时前`
  const day = Math.floor(hour / 24)
  if (day < 30) return `${day} 天前`
  return new Date(ts).toLocaleDateString('zh-CN')
}

const footText = computed(() => {
  if (props.visitedAt) return relativeTime(props.visitedAt)
  return props.project.created_at ? new Date(props.project.created_at).toLocaleDateString('zh-CN') : '-'
})
</script>

<style scoped>
.project-card {
  cursor: pointer;
  border-left: 3px solid var(--ax-brand);
  border-radius: var(--ax-radius-lg);
  transition: transform 0.15s;
}

.project-card:hover {
  transform: translateY(-2px);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ax-brand);
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-desc {
  color: var(--ax-text-secondary);
  font-size: 13px;
  height: 40px;
  overflow: hidden;
  margin-bottom: 12px;
}

.card-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.card-foot {
  display: flex;
  justify-content: space-between;
  color: var(--ax-text-placeholder);
  font-size: 12px;
}
</style>

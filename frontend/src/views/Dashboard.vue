<template>
  <div v-loading="loading">
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="item in statCards" :key="item.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" :style="{ background: item.color }">
            <el-icon :size="28"><component :is="item.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ item.value }}</div>
            <div class="stat-label">{{ item.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <span>快捷操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/ai-generate')">
              <el-icon><MagicStick /></el-icon> AI 生成用例
            </el-button>
            <el-button @click="$router.push('/projects')">
              <el-icon><Folder /></el-icon> 新建项目
            </el-button>
            <el-button @click="$router.push('/requirements')">
              <el-icon><Document /></el-icon> 添加需求
            </el-button>
            <el-button @click="$router.push('/testcases')">
              <el-icon><List /></el-icon> 查看用例
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <span>平台能力</span>
          </template>
          <ul class="feature-list">
            <li>基于 LLM 的智能用例生成</li>
            <li>需求-用例全生命周期管理</li>
            <li>用例评审与状态流转</li>
            <li>Excel 批量导出</li>
            <li>OpenAI 兼容 API 接入</li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { projectApi } from '@/api'

const loading = ref(false)
const stats = ref({
  project_count: 0,
  requirement_count: 0,
  testcase_count: 0,
  ai_generated_count: 0,
  pending_review_count: 0,
})

const statCards = computed(() => [
  { label: '项目数', value: stats.value.project_count, icon: 'Folder', color: '#3182ce' },
  { label: '需求数', value: stats.value.requirement_count, icon: 'Document', color: '#38a169' },
  { label: '用例总数', value: stats.value.testcase_count, icon: 'List', color: '#805ad5' },
  { label: '待评审', value: stats.value.pending_review_count, icon: 'Clock', color: '#dd6b20' },
])

onMounted(async () => {
  loading.value = true
  try {
    stats.value = await projectApi.dashboard()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stat-row {
  margin-bottom: 0;
}

.stat-card {
  display: flex;
  align-items: center;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #1a365d;
}

.stat-label {
  color: #718096;
  font-size: 14px;
  margin-top: 4px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.feature-list {
  list-style: none;
  padding: 0;
}

.feature-list li {
  padding: 8px 0;
  color: #4a5568;
  border-bottom: 1px dashed #e2e8f0;
}

.feature-list li:last-child {
  border-bottom: none;
}

.feature-list li::before {
  content: '✓ ';
  color: #38a169;
  font-weight: bold;
}
</style>

<template>
  <div class="a2-overview">
    <div class="a2-ov-card a2-ov-full">
      <div class="a2-ov-title">项目统计</div>
      <div class="a2-ov-stats">
        <div v-for="s in stats" :key="s.label" class="a2-ov-stat">
          <div class="a2-ov-num">{{ s.value }}</div>
          <div class="a2-ov-label">{{ s.label }}</div>
        </div>
      </div>
    </div>

    <div class="a2-ov-card a2-ov-16">
      <el-skeleton :rows="5" animated />
    </div>

    <div class="a2-ov-card a2-ov-8">
      <el-skeleton :rows="5" animated />
    </div>
  </div>
</template>

<script setup lang="ts">
const stats = [
  { value: 10, label: '接口数' },
  { value: 12, label: '接口用例数' },
  { value: 1, label: '文档数' },
  { value: 4, label: '数据模型数' },
  { value: 1, label: '测试场景数' },
]
</script>

<style scoped>
.a2-overview {
  display: grid;
  grid-template-columns: repeat(24, 1fr);
  gap: 8px;
  padding: 16px;
  width: 100%;
  overflow: hidden;
}

.a2-ov-card {
  border: 1px solid var(--a2-color-border-secondary);
  border-radius: 6px;
  padding: 8px;
}

.a2-ov-full {
  grid-column: span 24;
}

.a2-ov-16 {
  grid-column: span 16;
}

.a2-ov-8 {
  grid-column: span 8;
}

.a2-ov-title {
  margin-bottom: 16px;
  font-size: 18px;
}

.a2-ov-stats {
  display: flex;
  flex-wrap: wrap;
}

.a2-ov-stat {
  width: 20%;
}

.a2-ov-num {
  font-size: 24px;
}

.a2-ov-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--a2-color-text-tertiary);
}
</style>

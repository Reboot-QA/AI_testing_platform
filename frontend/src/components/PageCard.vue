<script setup>
// 通用页面内容容器：把「工具栏 + 表格/内容」装进统一白卡片（圆角/阴影/内边距）。
// 页面标题由 MainLayout 顶栏统一展示，故此卡片默认不重复标题。
// 用法：
//   <PageCard>
//     <template #toolbar> <el-button>新建</el-button> ...筛选项 </template>
//     <el-table ... />
//   </PageCard>
defineProps({
  // 内容区是否带内边距（表格类留 true；需要内容自行贴边时传 false）
  padded: { type: Boolean, default: true },
  // 撑满 el-main 剩余高度：卡片变纵向 flex，内容区 flex-1 内部滚动
  // （配合内部表格 height="100%"，实现表头/工具栏/分页固定、仅数据区滚动）
  fill: { type: Boolean, default: false },
})
</script>

<template>
  <section class="page-card" :class="{ 'page-card--fill': fill }">
    <div v-if="$slots.toolbar" class="page-card__toolbar">
      <slot name="toolbar" />
    </div>
    <div class="page-card__body" :class="{ 'page-card__body--flush': !padded }">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.page-card {
  background: var(--ax-bg);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  box-shadow: var(--ax-shadow-sm);
  padding: 20px;
}

.page-card__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

/* 工具栏内右对齐分组：<div class="page-card__spacer" /> 之后的元素靠右 */
.page-card__toolbar :deep(.page-card__spacer) {
  margin-left: auto;
}

.page-card__body--flush {
  margin: -20px;
}

/* 撑满高度模式：卡片纵向 flex，body 撑满剩余、内部滚动 */
.page-card--fill {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-card--fill .page-card__body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>

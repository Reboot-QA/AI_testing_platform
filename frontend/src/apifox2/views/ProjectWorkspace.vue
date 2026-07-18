<template>
  <div class="apifox2-workspace">
    <ApifoxLayout :key="projectId" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import ApifoxLayout from '@/apifox2/components/layout/ApifoxLayout.vue'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'
import { useApifox2TabStore } from '@/apifox2/stores/menuTab'
import '@/apifox2/styles/apifox2.css'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId ?? ''))

const menuStore = useApifox2MenuStore()
const tabStore = useApifox2TabStore()

onMounted(() => {
  // 纯 mock 数据：进入项目时初始化 Apifox 克隆的菜单与页签。
  menuStore.init()
  tabStore.init()
})
</script>

<style scoped>
.apifox2-workspace {
  height: calc(100vh - 100px);
  min-height: 0;
  overflow: hidden;
}
</style>

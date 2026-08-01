<template>
  <el-config-provider>
    <router-view />
    <AssistantPanel v-if="showAssistant" :key="assistantPanelKey" />
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AssistantPanel from '@/components/AssistantPanel.vue'
import { useUserStore } from '@/stores/user'
import { useSessionSync } from '@/composables/useSessionSync'

const route = useRoute()
const userStore = useUserStore()

// 多标签页共用 localStorage 的 token：别处换账号/登出后本页要跟着对齐，否则会拿新 token 打旧项目
useSessionSync()

const showAssistant = computed(
  () => userStore.isLoggedIn && route.path !== '/login' && route.path !== '/force-change-password',
)
const assistantPanelKey = computed(() => userStore.user?.id || userStore.token)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* 项目未引�?Tailwind Preflight（为兼容 Element Plus），需补回原生 <button> 边框重置�?   否则 shadcn 按钮会带浏览器默认的 2px outset 黑边（EP �?.el-button 特异度更高，不受影响）�?*/
button {
  border: 0;
}

html,
body,
#app {
  height: 100%;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
}
</style>

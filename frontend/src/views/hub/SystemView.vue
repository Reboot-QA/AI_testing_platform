<template>
  <div class="system-view">
    <div v-if="tiles.length" class="tiles">
      <div v-for="t in tiles" :key="t.path" class="sys-tile" @click="go(t.path)">
        <div class="ico" :style="{ backgroundColor: tint(t.color), color: t.color }">
          <el-icon :size="20"><component :is="t.icon" /></el-icon>
        </div>
        <div class="t-title">{{ t.title }}</div>
        <div class="t-desc">{{ t.desc }}</div>
      </div>
    </div>
    <el-empty v-else description="暂无系统管理权限，如需访问请联系管理员" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const tint = (color: string) => `color-mix(in srgb, ${color} 14%, white)`

const ALL = [
  {
    title: '全局设置',
    desc: 'LLM Provider · 通知 · 系统参数',
    icon: 'Setting',
    color: '#2b6cff',
    path: '/system/settings',
    perm: 'system_settings',
  },
  {
    title: '用户管理',
    desc: '账号 · 角色 · 状态',
    icon: 'User',
    color: '#0fc6c2',
    path: '/system/users',
    perm: 'system_users',
  },
  {
    title: '部门权限',
    desc: '部门 · 菜单权限分配',
    icon: 'OfficeBuilding',
    color: '#722ed1',
    path: '/system/departments',
    perm: 'system_departments',
  },
  {
    title: '日志',
    desc: '操作日志 · 错误日志',
    icon: 'Document',
    color: '#ff7d00',
    path: '/system/logs',
    perm: 'system_logs',
  },
]

const tiles = computed(() => ALL.filter((t) => userStore.hasPermission(t.perm)))

function go(path: string) {
  router.push(path)
}
</script>

<style scoped>
.system-view {
  height: 100%;
  min-height: 0;
  overflow-y: auto;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--ax-space-3);
}

.sys-tile {
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius-lg);
  background: var(--ax-bg);
  box-shadow: var(--ax-shadow-sm);
  padding: var(--ax-space-4);
  cursor: pointer;
  transition: all var(--ax-transition);
}

.sys-tile:hover {
  border-color: color-mix(in srgb, var(--ax-rail-active-bg) 30%, var(--ax-border));
  box-shadow: var(--ax-shadow);
}

.ico {
  width: 40px;
  height: 40px;
  border-radius: var(--ax-radius-lg);
  display: grid;
  place-items: center;
  margin-bottom: var(--ax-space-2-5);
}

.t-title {
  font-weight: 600;
  font-size: var(--ax-text-body-size);
  color: var(--ax-text);
}

.t-desc {
  margin-top: var(--ax-space-1);
  font-size: var(--ax-text-caption-size);
  color: var(--ax-text-tertiary);
}
</style>

<template>
  <div class="a2-sidenav">
    <div class="a2-sidenav-logo">
      <IconLogo />
    </div>

    <div class="a2-nav">
      <div
        class="a2-nav-item"
        :class="{ active: active === 'home' }"
        @click="emit('navigate', 'home')"
      >
        <svg
          aria-hidden="true"
          class="a2-nav-icon"
          fill="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            clip-rule="evenodd"
            d="M20 10H4v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8ZM9 13v-1h6v1c0 .6-.4 1-1 1h-4a1 1 0 0 1-1-1Z"
            fill-rule="evenodd"
          />
          <path d="M2 6c0-1.1.9-2 2-2h16a2 2 0 1 1 0 4H4a2 2 0 0 1-2-2Z" />
        </svg>
        <span class="a2-nav-name">接口管理</span>
      </div>

      <div
        class="a2-nav-item"
        :class="{ active: active === 'settings' }"
        @click="emit('navigate', 'settings')"
      >
        <svg
          aria-hidden="true"
          class="a2-nav-icon"
          fill="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            clip-rule="evenodd"
            d="M9.6 2.6A2 2 0 0 1 11 2h2a2 2 0 0 1 2 2l.5.3a2 2 0 0 1 2.9 0l1.4 1.3a2 2 0 0 1 0 2.9l.1.5h.1a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2l-.3.5a2 2 0 0 1 0 2.9l-1.3 1.4a2 2 0 0 1-2.9 0l-.5.1v.1a2 2 0 0 1-2 2h-2a2 2 0 0 1-2-2l-.5-.3a2 2 0 0 1-2.9 0l-1.4-1.3a2 2 0 0 1 0-2.9l-.1-.5H4a2 2 0 0 1-2-2v-2a2 2 0 0 1 2-2l.3-.5a2 2 0 0 1 0-2.9l1.3-1.4a2 2 0 0 1 2.9 0l.5-.1V4c0-.5.2-1 .6-1.4ZM8 12a4 4 0 1 1 8 0 4 4 0 0 1-8 0Z"
            fill-rule="evenodd"
          />
        </svg>
        <span class="a2-nav-name">项目配置</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import IconLogo from '@/apifox2/components/icons/IconLogo.vue'

defineProps<{ active: 'home' | 'settings' }>()
const emit = defineEmits<{ navigate: ['home' | 'settings'] }>()
</script>

<style scoped>
.a2-sidenav {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  flex-basis: 80px;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0 4px;
  padding-top: var(--layout-header-height);
}

.a2-sidenav-logo {
  margin: 8px 0 20px;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  padding: 6px;
  color: var(--a2-color-text);
  border: 1px solid var(--a2-color-border);
}

.a2-sidenav-logo :deep(svg) {
  width: 100%;
  height: 100%;
}

.a2-nav {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.a2-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--a2-color-text-secondary);
  text-decoration: none;
  transition: background-color 0.2s;
}

.a2-nav-item:hover {
  background-color: var(--a2-color-fill-tertiary);
}

.a2-nav-item.active {
  color: var(--a2-color-primary);
}

.a2-nav-icon {
  width: 24px;
  height: 24px;
}

.a2-nav-name {
  font-size: 12px;
}
</style>

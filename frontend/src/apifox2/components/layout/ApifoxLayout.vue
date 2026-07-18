<template>
  <div class="apifox2-root" :data-theme="dataTheme" :style="rootStyle">
    <SideNav :active="activeNav" @navigate="activeNav = $event" />

    <div class="a2-main">
      <div class="a2-main-header">
        <HeaderNav @open-settings="onOpenSettings" />
      </div>

      <div class="a2-main-body">
        <HomeContent v-if="activeNav === 'home'" @open-settings="onOpenSettings" />
        <SettingsPage v-else @open-settings="onOpenSettings" />
      </div>
    </div>

    <ModalsHost />
    <ModalSettings />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import SideNav from './SideNav.vue'
import HeaderNav from './HeaderNav.vue'
import HomeContent from '@/apifox2/components/HomeContent.vue'
import SettingsPage from '@/apifox2/components/SettingsPage.vue'
import ModalsHost from '@/apifox2/components/modals/ModalsHost.vue'
import ModalSettings from '@/apifox2/components/modals/ModalSettings.vue'
import { provideApifox2Layout } from '@/apifox2/composables/layout'
import { useApifox2Settings } from '@/apifox2/composables/useModals'
import { useApifox2Theme } from '@/apifox2/composables/theme'

provideApifox2Layout()
const { openSettings } = useApifox2Settings()
const { dataTheme, rootStyle } = useApifox2Theme()

const activeNav = ref<'home' | 'settings'>('home')

function onOpenSettings(key: string) {
  openSettings(key)
}
</script>

<style scoped>
.a2-main {
  display: flex;
  height: 100%;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
  padding-bottom: var(--p-main);
  padding-right: var(--p-main);
}

.a2-main-header {
  height: var(--layout-header-height);
  overflow: hidden;
}

.a2-main-body {
  position: relative;
  flex: 1;
  overflow-y: auto;
  border: 1px solid var(--a2-color-fill-secondary);
  background-color: var(--a2-color-bg-container);
  border-radius: 10px;
}
</style>

<template>
  <div class="a2-theme-editor">
    <!-- 主题 -->
    <div class="a2-te-row">
      <div class="a2-te-label">主题</div>
      <div class="a2-te-field a2-te-themes">
        <div
          v-for="(meta, mode) in presetThemes"
          :key="mode"
          class="a2-te-theme"
          :class="{ matched: themeSetting.themeMode === mode }"
          @click="setThemeSetting({ themeMode: mode })"
        >
          <div class="a2-te-preview" :class="meta.previewClass">
            <span class="pv-a" />
            <span class="pv-b" />
          </div>
          <span>{{ meta.name }}</span>
        </div>
      </div>
    </div>

    <!-- 主色 -->
    <div class="a2-te-row">
      <div class="a2-te-label">主色</div>
      <div class="a2-te-field a2-te-colors" :class="{ disabled: !isDefaultTheme }">
        <span
          v-for="color in presetColors"
          :key="color"
          class="a2-te-color"
          :class="{ matched: isDefaultTheme && color === themeSetting.colorPrimary }"
          :style="{
            backgroundColor: color,
            boxShadow:
              isDefaultTheme && color === themeSetting.colorPrimary
                ? `0 0 0 1px var(--a2-color-bg-container), 0 0 0 5px ${color}`
                : 'none',
          }"
          @click="isDefaultTheme && setThemeSetting({ colorPrimary: color })"
        />
      </div>
    </div>

    <!-- 圆角 -->
    <div class="a2-te-row">
      <div class="a2-te-label">圆角</div>
      <div class="a2-te-field a2-te-radius">
        <span
          v-for="radius in presetRadius"
          :key="radius"
          class="a2-te-radius-item"
          :class="{ matched: radius === themeSetting.borderRadius }"
          @click="setThemeSetting({ borderRadius: radius })"
        >
          <span class="a2-te-radius-inner" :style="{ borderRadius: `${radius}px` }" />
        </span>
      </div>
    </div>

    <!-- 页面空间 -->
    <div class="a2-te-row">
      <div class="a2-te-label">页面空间</div>
      <div class="a2-te-field">
        <el-radio-group
          :model-value="themeSetting.spaceType"
          @update:model-value="setThemeSetting({ spaceType: $event as 'default' | 'compact' })"
        >
          <el-radio value="default">适中</el-radio>
          <el-radio value="compact">紧凑</el-radio>
        </el-radio-group>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { presetColors, presetRadius, presetThemes } from './theme-data'
import { useApifox2Theme } from '@/apifox2/composables/theme'

const { themeSetting, setThemeSetting } = useApifox2Theme()

const isDefaultTheme = computed(
  () => themeSetting.themeMode === 'lightDefault' || themeSetting.themeMode === 'darkDefault',
)
</script>

<style scoped>
.a2-te-row {
  display: flex;
  margin-bottom: 20px;
}

.a2-te-label {
  width: 72px;
  flex-shrink: 0;
  color: var(--a2-color-text-secondary);
  padding-top: 4px;
}

.a2-te-field {
  flex: 1;
}

.a2-te-themes {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.a2-te-theme {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.a2-te-preview {
  position: relative;
  width: 120px;
  height: 80px;
  border-radius: 8px;
  overflow: hidden;
}

.a2-te-theme.matched .a2-te-preview {
  box-shadow:
    0 0 0 2px var(--a2-color-bg-container),
    0 0 0 5px var(--a2-color-primary);
}

.a2-te-preview .pv-a,
.a2-te-preview .pv-b {
  position: absolute;
  border-radius: 4px;
}

.a2-te-preview .pv-a {
  left: 12px;
  top: 12px;
  width: 66px;
  height: 50px;
}

.a2-te-preview .pv-b {
  left: 40px;
  top: 24px;
  width: 66px;
  height: 44px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
}

.preview-light {
  background: #edf1f7;
}
.preview-light .pv-a {
  background: #f1f5fa;
}
.preview-light .pv-b {
  background: #fff;
}

.preview-dark {
  background: #4f5155;
}
.preview-dark .pv-a {
  background: #292929;
}
.preview-dark .pv-b {
  background: #4f5155;
}

.preview-lark {
  background: #e1ede5;
}
.preview-lark .pv-a {
  background: #66c08d;
}
.preview-lark .pv-b {
  background: #fff;
}

.a2-te-colors {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  padding: 6px 0 0 8px;
}

.a2-te-colors.disabled {
  opacity: 0.5;
  pointer-events: none;
}

.a2-te-color {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  cursor: pointer;
  display: inline-block;
}

.a2-te-radius {
  display: flex;
  gap: 24px;
}

.a2-te-radius-item {
  position: relative;
  width: 48px;
  height: 48px;
  border-radius: 6px;
  cursor: pointer;
  overflow: hidden;
  background: var(--a2-color-fill-tertiary);
  display: inline-block;
}

.a2-te-radius-item.matched {
  background: rgba(255, 77, 79, 0.1);
}

.a2-te-radius-inner {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 100%;
  height: 100%;
  transform: translate(-50%, -50%) scale(1.25);
  border: 2px solid var(--a2-color-border);
}

.a2-te-radius-item.matched .a2-te-radius-inner {
  border-color: var(--a2-color-primary);
}
</style>

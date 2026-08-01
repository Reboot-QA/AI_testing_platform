<template>
  <button class="gr-btn" :class="{ active }" type="button">
    <span class="gr-ic"><slot name="icon" /></span>
    <span v-if="label" class="gr-label">{{ label }}</span>
    <span v-if="displayDot" class="gr-dot">{{ displayDot }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    label?: string
    active?: boolean
    dot?: number | string | null
  }>(),
  {
    label: '',
    active: false,
    dot: null,
  },
)

const displayDot = computed(() => {
  if (typeof props.dot === 'number') {
    if (props.dot <= 0) return ''
    return props.dot > 99 ? '99+' : String(props.dot)
  }
  return props.dot || ''
})
</script>

<style scoped>
.gr-btn {
  position: relative;
  width: calc(var(--ax-rail-width) - var(--ax-space-2));
  height: var(--ax-nav-primary-height);
  flex: none;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: var(--ax-space-0-5);
  padding: var(--ax-space-0);
  border: none;
  border-radius: var(--ax-radius-lg);
  background: transparent;
  color: var(--ax-rail-text);
  cursor: pointer;
  transition:
    background var(--ax-transition),
    color var(--ax-transition);
}

.gr-btn:hover {
  background: var(--ax-rail-hover-bg);
  color: var(--ax-rail-text-hover);
}

.gr-btn.active {
  background: var(--ax-rail-active-bg);
  color: var(--ax-rail-active-text);
  box-shadow: var(--ax-rail-active-glow);
  font-weight: 600;
}

.gr-ic {
  font-size: var(--ax-font-lg);
  line-height: 1;
  display: inline-flex;
}

.gr-label {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--ax-nav-primary-size);
  line-height: var(--ax-nav-primary-line);
}

.gr-dot {
  position: absolute;
  top: 2px;
  right: 6px;
  min-width: 14px;
  height: 14px;
  padding: 0 var(--ax-space-1);
  border-radius: 7px;
  background: var(--ax-tag-red-fg);
  color: var(--ax-rail-active-text);
  font-size: 10px;
  line-height: 14px;
  text-align: center;
  border: 2px solid var(--ax-raw-hex-eef4ff);
  box-sizing: content-box;
}
</style>

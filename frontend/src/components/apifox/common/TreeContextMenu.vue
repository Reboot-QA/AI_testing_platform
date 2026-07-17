<template>
  <teleport to="body">
    <ul v-if="visible" class="tree-ctx" :style="{ left: x + 'px', top: y + 'px' }">
      <li
        v-for="it in items"
        :key="it.key"
        :class="{ danger: it.danger }"
        @click="pick(it.key)"
      >
        {{ it.label }}
      </li>
    </ul>
  </teleport>
</template>

<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'

export interface TreeContextMenuItem {
  key: string
  label: string
  danger?: boolean
}

const props = withDefaults(
  defineProps<{
    visible?: boolean
    x?: number
    y?: number
    items?: TreeContextMenuItem[]
  }>(),
  {
    visible: false,
    x: 0,
    y: 0,
    items: () => [],
  },
)
const emit = defineEmits<{
  select: [key: string]
  close: []
}>()

function pick(key: string) {
  emit('select', key)
  emit('close')
}

function onDocClick() {
  if (props.visible) emit('close')
}

watch(
  () => props.visible,
  (v) => {
    if (v) document.addEventListener('click', onDocClick)
    else document.removeEventListener('click', onDocClick)
  }
)

onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.tree-ctx {
  position: fixed;
  z-index: 3000;
  min-width: 140px;
  margin: 0;
  padding: 4px 0;
  list-style: none;
  background: var(--ax-bg);
  border: 1px solid var(--ax-border);
  border-radius: var(--ax-radius);
  box-shadow: 0 4px 16px rgb(0 0 0 / 12%);
}

.tree-ctx li {
  padding: 6px 14px;
  font-size: 13px;
  color: var(--ax-text);
  cursor: pointer;
}

.tree-ctx li:hover {
  background: var(--ax-bg-hover);
}

.tree-ctx li.danger {
  color: var(--ax-danger);
}
</style>

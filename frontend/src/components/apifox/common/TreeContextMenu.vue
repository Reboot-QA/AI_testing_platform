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

<script setup>
import { onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  x: { type: Number, default: 0 },
  y: { type: Number, default: 0 },
  items: { type: Array, default: () => [] },
})
const emit = defineEmits(['select', 'close'])

function pick(key) {
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

<template>
  <span>
    <CircleXIcon
      v-if="isRemoveActive"
      class="a2-remove a2-remove-active"
      :size="13"
      @click="emit('remove')"
      @mouseleave="onLeave"
      @mouseover="isRemoveHover = true"
    />
    <CircleMinusIcon v-else class="a2-remove" :size="13" @click="activate" />
  </span>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { CircleMinusIcon, CircleXIcon } from 'lucide-vue-next'

const emit = defineEmits<{ remove: [] }>()

const isRemoveActive = ref(false)
const isRemoveHover = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined

function reset() {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    if (!isRemoveHover.value) isRemoveActive.value = false
  }, 1000)
}

function activate() {
  isRemoveActive.value = true
  reset()
}

function onLeave() {
  isRemoveHover.value = false
  reset()
}

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>

<style scoped>
.a2-remove {
  color: var(--a2-color-text-tertiary);
  cursor: pointer;
}

.a2-remove-active {
  color: var(--a2-color-red-6, #f5222d);
}
</style>

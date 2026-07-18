<template>
  <input
    class="a2-input-underline"
    :value="modelValue"
    :placeholder="placeholder"
    @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>

<script setup lang="ts">
defineProps<{
  modelValue?: string
  placeholder?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [string] }>()
</script>

<style scoped>
.a2-input-underline {
  color: var(--a2-color-text);
  border: none;
  border-bottom: 1px solid transparent;
  padding: 4px 4px;
  outline: none;
  background: transparent;
  font-weight: 600;
  width: 100%;
  transition: border-color 0.2s;
}

.a2-input-underline:hover {
  border-color: var(--a2-color-border);
}

.a2-input-underline:focus {
  border-color: var(--a2-color-primary);
}
</style>

<template>
  <div class="a2-search-box">
    <el-input
      v-model="keyword"
      :prefix-icon="SearchIconRender"
      clearable
      placeholder=""
      size="small"
      @input="onInput"
    />
  </div>
</template>

<script setup lang="ts">
import { h, ref } from 'vue'
import { SearchIcon } from 'lucide-vue-next'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

const menuStore = useApifox2MenuStore()
const keyword = ref('')

const SearchIconRender = () => h(SearchIcon, { size: 14 })

function onInput(val: string) {
  menuStore.setMenuSearchWord(val || undefined)
}
</script>

<style scoped>
.a2-search-box {
  flex: 1;
  overflow: hidden;
  border-radius: 6px;
  border: 1px solid var(--a2-color-border-secondary);
  transition: border-color 0.2s;
}

.a2-search-box:hover {
  border-color: var(--a2-color-primary);
}

.a2-search-box :deep(.el-input__wrapper) {
  box-shadow: none;
  background: transparent;
}
</style>

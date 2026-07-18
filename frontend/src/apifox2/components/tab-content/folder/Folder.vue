<template>
  <div class="a2-folder">
    <el-tabs v-model="activeKey" class="a2-folder-tabs">
      <el-tab-pane label="目录设置" name="settings">
        <div class="a2-folder-pane">
          <FolderSetting />
        </div>
      </el-tab-pane>
      <el-tab-pane label="全部接口" name="apis">
        <div class="a2-folder-pane">
          <FolderApiList />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FolderSetting from './FolderSetting.vue'
import FolderApiList from './FolderApiList.vue'

const activeKey = ref('settings')
</script>

<style scoped>
.a2-folder-tabs {
  padding: 0 16px;
}

.a2-folder-pane {
  padding: 16px;
}
</style>

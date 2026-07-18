<template>
  <div class="a2-folder-setting">
    <el-form label-width="110px" :model="form" @submit.prevent="save">
      <el-form-item label="目录名称" required>
        <el-input v-model="form.name" />
      </el-form-item>

      <el-form-item label="父级目录" required>
        <SelectorCatalog
          v-model="form.parentId"
          :type="MenuItemType.ApiDetailFolder"
          :exclued="apiFolder ? [apiFolder.id] : undefined"
        />
      </el-form-item>

      <el-form-item label="服务（前置URL）">
        <SelectorService v-model="form.serverId" />
      </el-form-item>

      <el-form-item label="备注">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="4"
          placeholder="如需展示在发布的文档中，请在“文档” Tab 里编辑"
        />
      </el-form-item>

      <el-form-item label=" ">
        <el-button type="primary" @click="save">保存</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SelectorCatalog from '@/apifox2/components/SelectorCatalog.vue'
import SelectorService from '@/apifox2/components/SelectorService.vue'
import { ROOT_CATALOG, SERVER_INHERIT } from '@/apifox2/configs/static'
import { MenuItemType } from '@/apifox2/enums'
import { useTabContentContext } from '@/apifox2/composables/useTabContent'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

const menuStore = useApifox2MenuStore()
const { tabData } = useTabContentContext()

const form = reactive<{
  name?: string
  parentId?: string
  serverId?: string
  description?: string
}>({ name: '', parentId: ROOT_CATALOG, serverId: SERVER_INHERIT, description: '' })

const apiFolder = computed(() => menuStore.menuRawList?.find(({ id }) => id === tabData.key))

watch(
  apiFolder,
  (folder) => {
    if (folder && folder.type === MenuItemType.ApiDetailFolder) {
      form.name = folder.name
      form.parentId = folder.parentId ?? ROOT_CATALOG
      form.serverId = folder.data?.serverId ?? SERVER_INHERIT
      form.description = folder.data?.description
    }
  },
  { immediate: true },
)

function save() {
  if (!form.name?.trim()) {
    ElMessage.warning('目录名称不能为空')
    return
  }
  const folder = apiFolder.value
  if (folder) {
    menuStore.updateMenuItem({
      id: folder.id,
      name: form.name,
      parentId: form.parentId === ROOT_CATALOG ? undefined : form.parentId,
      data: { serverId: form.serverId, description: form.description },
    } as never)
  }
}
</script>

<style scoped>
.a2-folder-setting {
  max-width: 42rem;
}
</style>

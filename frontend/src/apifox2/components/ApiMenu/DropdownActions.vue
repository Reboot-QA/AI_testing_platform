<template>
  <el-dropdown
    :trigger="trigger"
    placement="bottom-start"
    popper-class="a2-actions-dropdown"
    @command="onCommand"
    @click.stop
  >
    <slot />
    <template #dropdown>
      <el-dropdown-menu>
        <template v-if="isFolder">
          <el-dropdown-item command="create">
            <FileIcon :type="createType" :size="14" class="a2-act-icon a2-act-primary" />{{
              tipTitle
            }}
          </el-dropdown-item>
          <el-dropdown-item divided command="rename">
            <PencilIcon :size="14" class="a2-act-icon" />重命名
          </el-dropdown-item>
          <el-dropdown-item command="copy">
            <CopyIcon :size="14" class="a2-act-icon" />复制
          </el-dropdown-item>
          <el-dropdown-item command="move">
            <FolderInputIcon :size="14" class="a2-act-icon" />移动到
          </el-dropdown-item>
          <el-dropdown-item divided command="new">
            <FolderPlusIcon :size="14" class="a2-act-icon" />添加子目录
          </el-dropdown-item>
          <el-dropdown-item divided command="delete">
            <TrashIcon :size="14" class="a2-act-icon" />删除
          </el-dropdown-item>
        </template>
        <template v-else>
          <el-dropdown-item command="rename">
            <PencilIcon :size="14" class="a2-act-icon" />重命名
          </el-dropdown-item>
          <el-dropdown-item command="copy">
            <CopyIcon :size="14" class="a2-act-icon" />复制
          </el-dropdown-item>
          <el-dropdown-item command="move">
            <FolderInputIcon :size="14" class="a2-act-icon" />移动到
          </el-dropdown-item>
          <el-dropdown-item divided command="delete">
            <TrashIcon :size="14" class="a2-act-icon" />删除
          </el-dropdown-item>
        </template>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessageBox } from 'element-plus'
import { CopyIcon, FolderInputIcon, FolderPlusIcon, PencilIcon, TrashIcon } from 'lucide-vue-next'
import FileIcon from '@/apifox2/components/icons/FileIcon.vue'
import { nanoid } from '@/apifox2/lib/nanoid'
import { API_MENU_CONFIG } from '@/apifox2/configs/static'
import { MenuItemType } from '@/apifox2/enums'
import { getCatalogType, getCreateType } from '@/apifox2/helpers'
import type { ApiMenuData } from '@/apifox2/components/ApiMenu/ApiMenu.type'
import { useHelpers } from '@/apifox2/composables/useHelpers'
import {
  useApifox2Rename,
  useApifox2MoveMenu,
  useApifox2NewCatalog,
} from '@/apifox2/composables/useModals'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

const props = withDefaults(
  defineProps<{
    catalog: ApiMenuData
    isFolder?: boolean
    trigger?: 'contextmenu' | 'click' | 'hover'
  }>(),
  { isFolder: false, trigger: 'click' },
)

const menuStore = useApifox2MenuStore()
const { createTabItem } = useHelpers()
const { openRename } = useApifox2Rename()
const { openMoveMenu } = useApifox2MoveMenu()
const { openNewCatalog } = useApifox2NewCatalog()

const tipTitle = computed(() => API_MENU_CONFIG[getCatalogType(props.catalog.type)].tipTitle)
const createType = computed(() => getCreateType(props.catalog.type))

function onCommand(command: string) {
  const catalog = props.catalog
  switch (command) {
    case 'create':
      createTabItem(createType.value)
      break
    case 'rename':
      openRename({ id: catalog.id, name: catalog.name })
      break
    case 'copy':
      menuStore.addMenuItem({ ...catalog, id: nanoid(6) })
      break
    case 'move':
      openMoveMenu({ id: catalog.id }, catalog.type)
      break
    case 'new':
      openNewCatalog({ parentId: catalog.id, type: catalog.type })
      break
    case 'delete':
      confirmDelete()
      break
  }
}

function confirmDelete() {
  const catalog = props.catalog
  const isFolder = props.isFolder

  let content: string
  if (isFolder) {
    content = `${
      catalog.type === MenuItemType.ApiDetailFolder
        ? '该目录及该目录下的接口和用例都'
        : catalog.type === MenuItemType.ApiSchemaFolder
          ? '该目录及该目录下的数据模型都'
          : ''
    }将移至回收站，30 天后自动彻底删除。`
  } else {
    content = `${
      catalog.type === MenuItemType.ApiDetail
        ? '该接口和该接口下的用例都'
        : catalog.type === MenuItemType.Doc
          ? '文档'
          : catalog.type === MenuItemType.ApiSchema
            ? '该数据模型'
            : ''
    }将移至回收站，30 天后自动彻底删除。`
  }

  const titlePrefix = isFolder
    ? '删除目录'
    : `删除${API_MENU_CONFIG[getCatalogType(catalog.type)].title}`

  ElMessageBox.confirm(content, `${titlePrefix}“${catalog.name}”？`, {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    confirmButtonClass: 'el-button--danger',
  })
    .then(() => menuStore.removeMenuItem({ id: catalog.id }))
    .catch(() => {})
}
</script>

<style scoped>
.a2-act-icon {
  margin-right: 6px;
}

.a2-act-primary {
  color: var(--a2-color-primary);
}
</style>

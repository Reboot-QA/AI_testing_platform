<template>
  <!-- 新建目录 -->
  <el-dialog v-model="state.newCatalog.visible" title="新建目录" width="400px" append-to-body>
    <el-form label-position="top">
      <el-form-item label="名称" required>
        <el-input ref="newCatalogNameRef" v-model="newCatalogName" />
      </el-form-item>
      <el-form-item label="父级目录" required>
        <SelectorCatalog v-model="newCatalogParentId" :type="state.newCatalog.type" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="state.newCatalog.visible = false">取消</el-button>
      <el-button type="primary" @click="confirmNewCatalog">确定</el-button>
    </template>
  </el-dialog>

  <!-- 重命名 -->
  <el-dialog v-model="state.rename.visible" title="重命名" width="416px" append-to-body>
    <el-form label-position="top">
      <el-form-item label="名称" required>
        <el-input ref="renameNameRef" v-model="renameName" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="state.rename.visible = false">取消</el-button>
      <el-button type="primary" @click="confirmRename">确定</el-button>
    </template>
  </el-dialog>

  <!-- 移动到... -->
  <el-dialog v-model="state.moveMenu.visible" title="移动到..." width="416px" append-to-body>
    <el-form label-position="top">
      <el-form-item label="目标目录" required>
        <SelectorCatalog v-model="moveParentId" placeholder="移动到..." :type="moveSelectorType" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="state.moveMenu.visible = false">取消</el-button>
      <el-button type="primary" @click="confirmMove">确定</el-button>
    </template>
  </el-dialog>
  <!-- 设置弹窗由 ModalSettings.vue 承载 -->
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import SelectorCatalog from '@/apifox2/components/SelectorCatalog.vue'
import { nanoid } from '@/apifox2/lib/nanoid'
import { ROOT_CATALOG } from '@/apifox2/configs/static'
import { MenuItemType } from '@/apifox2/enums'
import { useApifox2Modals } from '@/apifox2/composables/useModals'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

const { state } = useApifox2Modals()
const menuStore = useApifox2MenuStore()

// —— 新建目录 ——
const newCatalogName = ref('')
const newCatalogParentId = ref<string | undefined>(ROOT_CATALOG)
const newCatalogNameRef = ref()

watch(
  () => state.newCatalog.visible,
  (v) => {
    if (v) {
      newCatalogName.value = ''
      newCatalogParentId.value = state.newCatalog.parentId ?? ROOT_CATALOG
      nextTick(() => newCatalogNameRef.value?.focus())
    }
  },
)

function confirmNewCatalog() {
  if (!newCatalogName.value.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  if (!state.newCatalog.type) return
  menuStore.addMenuItem({
    id: nanoid(6),
    name: newCatalogName.value,
    type: state.newCatalog.type,
    parentId: newCatalogParentId.value === ROOT_CATALOG ? undefined : newCatalogParentId.value,
  } as never)
  state.newCatalog.visible = false
}

// —— 重命名 ——
const renameName = ref('')
const renameNameRef = ref()

watch(
  () => state.rename.visible,
  (v) => {
    if (v) {
      renameName.value = state.rename.name ?? ''
      nextTick(() => renameNameRef.value?.select?.())
    }
  },
)

function confirmRename() {
  if (!renameName.value.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  if (state.rename.id) {
    menuStore.updateMenuItem({ id: state.rename.id, name: renameName.value })
  }
  state.rename.visible = false
}

// —— 移动到... ——
const moveParentId = ref<string | undefined>()

watch(
  () => state.moveMenu.visible,
  (v) => {
    if (v) {
      moveParentId.value = state.moveMenu.parentId
    }
  },
)

const moveSelectorType = computed(() => {
  const t = state.moveMenu.menuItemType
  if (t === MenuItemType.ApiDetail) return MenuItemType.ApiDetailFolder
  if (t === MenuItemType.ApiSchema) return MenuItemType.ApiSchemaFolder
  return t
})

function confirmMove() {
  if (state.moveMenu.id) {
    menuStore.updateMenuItem({
      id: state.moveMenu.id,
      parentId: moveParentId.value === ROOT_CATALOG ? undefined : moveParentId.value,
    })
  }
  state.moveMenu.visible = false
}
</script>

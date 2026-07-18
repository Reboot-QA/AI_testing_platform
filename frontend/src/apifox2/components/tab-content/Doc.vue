<template>
  <div v-if="editing" class="a2-doc a2-doc-editing">
    <div class="a2-doc-head">
      <InputUnderline v-model="name" :placeholder="DEFAULT_DOC_NAME" class="a2-doc-name" />
      <div class="a2-doc-actions">
        <el-button v-if="!isCreating" @click="editing = false">退出编辑</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </div>
    </div>
    <div class="a2-doc-body">
      <MarkdownEditor :value="content" @change="content = $event" />
    </div>
  </div>

  <div v-else class="a2-doc">
    <div class="a2-doc-head">
      <div class="a2-doc-title">{{ docValue?.name }}</div>
      <el-button @click="editing = true">编辑</el-button>
    </div>
    <div class="a2-doc-view-wrap">
      <div class="a2-doc-view">
        <Viewer :value="docValue?.content ?? ''" :plugins="viewerPlugins" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Viewer } from '@bytemd/vue-next'
import gfm from '@bytemd/plugin-gfm'
import 'bytemd/dist/index.css'
import { ElMessage } from 'element-plus'
import InputUnderline from '@/apifox2/components/InputUnderline.vue'
import MarkdownEditor from '@/apifox2/components/MarkdownEditor.vue'
import { nanoid } from '@/apifox2/lib/nanoid'
import { PageTabStatus } from '@/apifox2/components/ApiTab/ApiTab.enum'
import { MenuItemType } from '@/apifox2/enums'
import type { ApiDoc } from '@/apifox2/types'
import { useTabContentContext } from '@/apifox2/composables/useTabContent'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'
import { useApifox2TabStore } from '@/apifox2/stores/menuTab'

const DEFAULT_DOC_NAME = '未命名文档'
const viewerPlugins = [gfm()]

const { tabData } = useTabContentContext()
const menuStore = useApifox2MenuStore()
const tabStore = useApifox2TabStore()

const docValue = computed<ApiDoc | undefined>(
  () => menuStore.menuRawList?.find(({ id }) => id === tabData.key)?.data as ApiDoc | undefined,
)

const name = ref<string | undefined>()
const content = ref('')

watch(
  docValue,
  (v) => {
    if (v) {
      name.value = v.name
      content.value = v.content ?? ''
    }
  },
  { immediate: true },
)

const isCreating = tabData.data?.tabStatus === PageTabStatus.Create
const editing = ref(isCreating)

function save() {
  const values: ApiDoc = {
    id: nanoid(6),
    name: name.value ?? DEFAULT_DOC_NAME,
    content: content.value,
  }

  if (isCreating) {
    const menuItemId = nanoid(6)
    menuStore.addMenuItem({
      id: menuItemId,
      name: name.value ?? DEFAULT_DOC_NAME,
      type: MenuItemType.Doc,
      data: values,
    })
    tabStore.addTabItem(
      { key: menuItemId, label: name.value, contentType: MenuItemType.Doc },
      { replaceTab: tabData.key },
    )
  } else {
    menuStore.updateMenuItem({ id: tabData.key, name: name.value, data: values })
    ElMessage.success('已保存')
  }
}
</script>

<style scoped>
.a2-doc {
  display: flex;
  height: 100%;
  flex-direction: column;
  overflow: hidden;
}

.a2-doc-head {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  gap: 8px;
}

.a2-doc-name {
  font-weight: bold;
  font-size: 18px;
}

.a2-doc-title {
  flex: 1;
  font-size: 18px;
  font-weight: bold;
}

.a2-doc-actions {
  display: flex;
  gap: 8px;
}

.a2-doc-body {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.a2-doc-view-wrap {
  flex: 1;
  overflow: auto;
  min-height: 0;
}

.a2-doc-view {
  margin: 0 auto;
  max-width: 1512px;
  padding: 8px;
}
</style>

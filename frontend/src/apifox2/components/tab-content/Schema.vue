<template>
  <div class="a2-schema">
    <div class="a2-schema-head">
      <InputUnderline
        v-model="schemaName"
        placeholder="数据模型名称，建议使用代码模型名称或同义词"
      />
      <div class="a2-schema-actions">
        <el-button type="primary" @click="save">保存</el-button>
        <el-popconfirm
          v-if="!isCreating"
          :title="`确定删除数据模型“${schemaName ?? ''}”？`"
          placement="bottom"
          @confirm="remove"
        >
          <template #reference>
            <el-button>删除</el-button>
          </template>
        </el-popconfirm>
      </div>
    </div>

    <JsonSchemaCard
      :value="jsonSchema"
      :editor-props="{ defaultExpandAll: true }"
      @change="onSchemaChange"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import InputUnderline from '@/apifox2/components/InputUnderline.vue'
import JsonSchemaCard from '@/apifox2/components/JsonSchemaCard.vue'
import { nanoid } from '@/apifox2/lib/nanoid'
import { deepClone } from '@/apifox2/utils'
import { PageTabStatus } from '@/apifox2/components/ApiTab/ApiTab.enum'
import { initialCreateApiSchemaData } from '@/apifox2/data/remote'
import { MenuItemType } from '@/apifox2/enums'
import type { JsonSchema } from '@/apifox2/json-schema'
import type { ApiSchema } from '@/apifox2/types'
import { useTabContentContext } from '@/apifox2/composables/useTabContent'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'
import { useApifox2TabStore } from '@/apifox2/stores/menuTab'

const { tabData } = useTabContentContext()
const menuStore = useApifox2MenuStore()
const tabStore = useApifox2TabStore()

const isCreating = tabData.data?.tabStatus === PageTabStatus.Create

const schemaName = ref<string | undefined>()
const jsonSchema = ref<JsonSchema | undefined>()

const fieldsValue = computed<(ApiSchema & { name?: string }) | undefined>(() => {
  if (isCreating) {
    return { ...initialCreateApiSchemaData }
  }
  const menuData = menuStore.menuRawList?.find(({ id }) => id === tabData.key)
  if (menuData && menuData.type === MenuItemType.ApiSchema && menuData.data) {
    return { ...menuData.data, name: menuData.name }
  }
  return undefined
})

watch(
  fieldsValue,
  (v) => {
    if (v) {
      schemaName.value = v.name
      jsonSchema.value = deepClone(v.jsonSchema)
    }
  },
  { immediate: true },
)

function onSchemaChange(v: JsonSchema | undefined) {
  jsonSchema.value = v
}

function save() {
  const menuName = schemaName.value ?? '未命名数据模型'
  const values: ApiSchema = { jsonSchema: jsonSchema.value as JsonSchema }

  if (isCreating) {
    const menuItemId = nanoid(6)
    menuStore.addMenuItem({
      id: menuItemId,
      name: menuName,
      type: MenuItemType.ApiSchema,
      data: values,
    })
    tabStore.addTabItem(
      { key: menuItemId, label: menuName, contentType: MenuItemType.ApiSchema },
      { replaceTab: tabData.key },
    )
  } else {
    menuStore.updateMenuItem({ id: tabData.key, name: menuName, data: values })
    ElMessage.success('保存成功')
  }
}

function remove() {
  tabStore.removeTabItem({ key: tabData.key })
  menuStore.removeMenuItem({ id: tabData.key })
}
</script>

<style scoped>
.a2-schema {
  padding: 16px;
}

.a2-schema-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.a2-schema-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
</style>

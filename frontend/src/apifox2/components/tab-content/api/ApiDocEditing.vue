<template>
  <div class="a2-apiedit">
    <div class="a2-apiedit-head">
      <div class="a2-apiedit-pathrow">
        <el-select v-model="form.method" filterable class="a2-method-select">
          <el-option v-for="o in methodOptions" :key="o.value" :value="o.value" :label="o.value">
            <span :style="{ color: `var(${o.color})`, fontWeight: 600 }">{{ o.value }}</span>
          </el-option>
        </el-select>
        <PathInput
          v-model="form.path"
          class="a2-path"
          @value-change="handlePathChange"
          @parse-query-params="handleParseQueryParams"
        />
      </div>

      <div class="a2-apiedit-actions">
        <el-button type="primary" @click="save">保存</el-button>
        <template v-if="!isCreating">
          <el-button>运行</el-button>
          <ApiRemoveButton :tab-key="tabData.key" />
        </template>
      </div>
    </div>

    <div class="a2-apiedit-body">
      <InputUnderline v-model="form.name" :placeholder="DEFAULT_NAME" />

      <div class="a2-apiedit-base">
        <BaseFormItems :model="form" @update="onBaseUpdate" />
      </div>

      <GroupTitle class="a2-mt2">请求参数</GroupTitle>
      <ParamsTab
        :value="form.parameters"
        :request-body="form.requestBody"
        @change="form.parameters = $event"
        @body-change="form.requestBody = $event"
      />

      <GroupTitle class="a2-mt8 a2-mb3">返回响应</GroupTitle>
      <ResponseTab
        :value="form.responses"
        :response-examples="form.responseExamples"
        @change="form.responses = $event"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import InputUnderline from '@/apifox2/components/InputUnderline.vue'
import ApiRemoveButton from './ApiRemoveButton.vue'
import BaseFormItems from './components/BaseFormItems.vue'
import GroupTitle from './components/GroupTitle.vue'
import PathInput from './components/PathInput.vue'
import ParamsTab from './params/ParamsTab.vue'
import ResponseTab from './components/ResponseTab.vue'
import { methodOptions } from './options'
import { nanoid } from '@/apifox2/lib/nanoid'
import { deepClone } from '@/apifox2/utils'
import { PageTabStatus } from '@/apifox2/components/ApiTab/ApiTab.enum'
import { initialCreateApiDetailsData } from '@/apifox2/data/remote'
import { MenuItemType, ParamType } from '@/apifox2/enums'
import type { ApiDetails } from '@/apifox2/types'
import { useTabContentContext } from '@/apifox2/composables/useTabContent'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'
import { useApifox2TabStore } from '@/apifox2/stores/menuTab'

const DEFAULT_NAME = '未命名接口'

const { tabData } = useTabContentContext()
const menuStore = useApifox2MenuStore()
const tabStore = useApifox2TabStore()

const isCreating = tabData.data?.tabStatus === PageTabStatus.Create

const form = reactive<ApiDetails>(deepClone(initialCreateApiDetailsData))

function loadForm() {
  if (isCreating) {
    Object.assign(form, deepClone(initialCreateApiDetailsData))
    return
  }
  const menuData = menuStore.menuRawList?.find(({ id }) => id === tabData.key)
  if (
    menuData &&
    (menuData.type === MenuItemType.ApiDetail || menuData.type === MenuItemType.HttpRequest) &&
    menuData.data
  ) {
    // 清空后写入，保持 reactive 引用。
    Object.keys(form).forEach((k) => delete (form as Record<string, unknown>)[k])
    Object.assign(form, deepClone(menuData.data))
  }
}

watch(() => menuStore.menuRawList, loadForm, { immediate: true })

function onBaseUpdate(patch: Partial<ApiDetails>) {
  Object.assign(form, patch)
}

function save() {
  const menuName = form.name ?? DEFAULT_NAME
  const data = { ...deepClone(form), name: menuName }

  if (isCreating) {
    const menuItemId = nanoid(6)
    menuStore.addMenuItem({
      id: menuItemId,
      name: menuName,
      type: MenuItemType.ApiDetail,
      data,
    })
    tabStore.addTabItem(
      { key: menuItemId, label: menuName, contentType: MenuItemType.ApiDetail },
      { replaceTab: tabData.key },
    )
  } else {
    menuStore.updateMenuItem({ id: tabData.key, name: menuName, data })
    ElMessage.success('保存成功')
  }
}

/** 从接口路径提取 {param} 形式的 Path 参数，与已有 path 参数对齐。 */
function handlePathChange(pathVal: string | undefined) {
  if (typeof pathVal !== 'string') return
  const regex = /\{+([^{}/]+)\}+/g
  let match: RegExpExecArray | null
  const pathParams: string[] = []
  while ((match = regex.exec(pathVal)) !== null) {
    if (match[1]) pathParams.push(match[1])
  }

  const oldPath = form.parameters?.path
  const oldLen = oldPath?.length ?? 0

  let newPath: typeof oldPath
  if (pathParams.length >= oldLen) {
    const acc = [...(oldPath ?? [])]
    pathParams.forEach((cur, curIdx) => {
      const target = oldPath?.[curIdx]
      if (target) {
        acc.splice(curIdx, 1, { ...target, name: cur })
      } else {
        acc.push({ id: nanoid(4), name: cur, type: ParamType.String, required: true })
      }
    })
    newPath = acc
  } else {
    newPath = oldPath?.slice(0, pathParams.length)
  }

  form.parameters = { ...form.parameters, path: newPath }
}

function handleParseQueryParams(parsed: import('@/apifox2/types').Parameter[] | undefined) {
  if (!Array.isArray(parsed)) return
  const current = form.parameters?.query
  let newQuery = parsed
  if (Array.isArray(current)) {
    newQuery = parsed.reduce(
      (acc, item) => {
        if (!acc.find(({ name }) => name === item.name)) acc.push(item)
        return acc
      },
      [...current],
    )
  }
  form.parameters = { ...form.parameters, query: newQuery }
  ElMessage.info('路径中 Query 参数已自动提取，并填充到下方「请求参数」的 Params 中')
}
</script>

<style scoped>
.a2-apiedit {
  display: flex;
  height: 100%;
  flex-direction: column;
}

.a2-apiedit-head {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  gap: 8px;
}

.a2-apiedit-pathrow {
  display: flex;
  flex: 1;
}

.a2-method-select {
  min-width: 110px;
}

.a2-method-select :deep(.el-select__wrapper) {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.a2-path {
  flex: 1;
}

.a2-path :deep(.el-input__wrapper) {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

.a2-apiedit-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
  padding-left: 8px;
}

.a2-apiedit-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.a2-apiedit-base {
  padding-top: 8px;
}

.a2-mt2 {
  margin-top: 8px;
}

.a2-mt8 {
  margin-top: 32px;
}

.a2-mb3 {
  margin-bottom: 12px;
}
</style>

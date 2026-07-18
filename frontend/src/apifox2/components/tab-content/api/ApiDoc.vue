<template>
  <div v-if="docValue && methodConfig" class="a2-apidoc">
    <div class="a2-apidoc-titlerow">
      <div class="a2-apidoc-title-group">
        <h2 class="a2-apidoc-name">{{ docValue.name }}</h2>
        <el-tooltip content="复制 ID" placement="top">
          <el-button class="a2-apidoc-id" size="small" link type="primary" @click="copyId">
            #{{ docValue.id }}
          </el-button>
        </el-tooltip>
      </div>

      <div class="a2-apidoc-actions">
        <el-button type="primary"><ZapIcon :size="14" class="a2-ic" />运行</el-button>
        <el-button><Code2Icon :size="14" class="a2-ic" />生成代码</el-button>
        <ApiRemoveButton :tab-key="tabData.key" />
      </div>
    </div>

    <div class="a2-apidoc-methodrow">
      <span class="a2-apidoc-method" :style="{ backgroundColor: `var(${methodConfig.color})` }">
        {{ docValue.method }}
      </span>
      <span class="a2-apidoc-path">{{ docValue.path }}</span>
      <el-select :model-value="docValue.status" style="width: 120px">
        <el-option v-for="o in statusOptions" :key="o.value" :value="o.value" :label="o.text" />
      </el-select>
    </div>

    <div v-if="docValue.tags?.length" class="a2-apidoc-tags">
      <span v-for="tag in docValue.tags" :key="tag" class="a2-apidoc-tag">{{ tag }}</span>
    </div>

    <div class="a2-apidoc-baseinfo">
      <div>
        <span class="k">创建时间</span><span class="v">{{ formatCnDate(docValue.createdAt) }}</span>
      </div>
      <div>
        <span class="k">修改时间</span><span class="v">{{ formatCnDate(docValue.updatedAt) }}</span>
      </div>
      <div>
        <span class="k">修改者</span><span class="v">{{ creator.name }}</span>
      </div>
      <div>
        <span class="k">创建者</span><span class="v">{{ creator.name }}</span>
      </div>
      <div>
        <span class="k">责任人</span><span class="v">{{ creator.name }}</span>
      </div>
    </div>

    <div v-if="docValue.description">
      <GroupTitle>接口说明</GroupTitle>
      <Viewer :value="docValue.description" :plugins="viewerPlugins" />
    </div>

    <div>
      <GroupTitle>请求参数</GroupTitle>
      <div v-if="hasParams" class="a2-apidoc-params">
        <div v-if="pathParams?.length" class="a2-apidoc-card">
          <div class="a2-apidoc-card-head">Path 参数</div>
          <div class="a2-apidoc-card-body">
            <ApiParamItem v-for="p in pathParams" :key="p.id" :param="p" />
          </div>
        </div>
        <div v-if="queryParams?.length" class="a2-apidoc-card">
          <div class="a2-apidoc-card-head">Query 参数</div>
          <div class="a2-apidoc-card-body">
            <ApiParamItem v-for="p in queryParams" :key="p.id" :param="p" />
          </div>
        </div>
      </div>
      <span v-else>无</span>
    </div>

    <div v-if="docValue.responses">
      <GroupTitle>返回响应</GroupTitle>
      <el-tabs type="card" class="a2-apidoc-resp">
        <el-tab-pane
          v-for="res in docValue.responses"
          :key="res.id"
          :name="res.id"
          :label="`${res.name}(${res.code})`"
        >
          <div class="a2-apidoc-resp-info">
            <span><span class="k">HTTP 状态码：</span>{{ res.code }}</span>
            <span><span class="k">内容格式：</span>{{ res.contentType }}</span>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h } from 'vue'
import { Viewer } from '@bytemd/vue-next'
import gfm from '@bytemd/plugin-gfm'
import 'bytemd/dist/index.css'
import { ElMessage } from 'element-plus'
import { Code2Icon, ZapIcon } from 'lucide-vue-next'
import ApiRemoveButton from './ApiRemoveButton.vue'
import GroupTitle from './components/GroupTitle.vue'
import { statusOptions, formatCnDate } from './options'
import { HTTP_METHOD_CONFIG } from '@/apifox2/configs/static'
import { creator } from '@/apifox2/data/remote'
import type { ApiDetails, Parameter } from '@/apifox2/types'
import { useTabContentContext } from '@/apifox2/composables/useTabContent'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'

const { tabData } = useTabContentContext()
const menuStore = useApifox2MenuStore()

const viewerPlugins = [gfm()]

const docValue = computed(
  () => menuStore.menuRawList?.find(({ id }) => id === tabData.key)?.data as ApiDetails | undefined,
)
const methodConfig = computed(() =>
  docValue.value ? HTTP_METHOD_CONFIG[docValue.value.method] : undefined,
)

const pathParams = computed(() => docValue.value?.parameters?.path)
const queryParams = computed(() => docValue.value?.parameters?.query)
const hasParams = computed(() => !!pathParams.value?.length || !!queryParams.value?.length)

function copyId() {
  if (docValue.value) {
    void navigator.clipboard.writeText(docValue.value.id).then(() => ElMessage.success('已复制'))
  }
}

// 单个参数展示（内联子组件，对应 ApiParameter）。
const ApiParamItem = defineComponent({
  props: { param: { type: Object as () => Parameter, required: true } },
  setup(p) {
    return () => {
      const param = p.param
      const isLong = param.description?.includes('\n')
      return h('div', { class: 'a2-param' }, [
        h('div', { class: 'a2-param-line' }, [
          h('span', { class: 'a2-param-name' }, param.name),
          h('span', { class: 'a2-param-type' }, param.type),
          !isLong ? h('span', { class: 'a2-param-desc' }, param.description) : null,
        ]),
        isLong ? h('div', { class: 'a2-param-longdesc' }, param.description) : null,
        h('div', { class: 'a2-param-example' }, [
          h('span', '示例值：'),
          h(
            'span',
            { class: 'a2-param-example-val' },
            Array.isArray(param.example) ? param.example.join(',') : param.example,
          ),
        ]),
      ])
    }
  },
})
</script>

<style scoped>
.a2-apidoc {
  height: 100%;
  overflow: auto;
  padding: 16px;
}

.a2-apidoc-titlerow {
  display: flex;
  align-items: center;
}

.a2-apidoc-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.a2-apidoc-name {
  font-size: 16px;
  font-weight: 600;
}

.a2-apidoc-actions {
  margin-left: auto;
  display: flex;
  gap: 8px;
  padding-left: 8px;
}

.a2-ic {
  margin-right: 4px;
}

.a2-apidoc-methodrow {
  display: flex;
  align-items: center;
  margin: 12px 0;
  gap: 8px;
}

.a2-apidoc-method {
  padding: 2px 8px;
  font-size: 12px;
  line-height: 1.5;
  font-weight: bold;
  color: #fff;
  border-radius: 4px;
}

.a2-apidoc-tags {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.a2-apidoc-tag {
  padding: 2px 8px;
  font-size: 12px;
  color: var(--a2-color-primary);
  background-color: rgba(255, 77, 79, 0.1);
  border-radius: 2px;
}

.a2-apidoc-baseinfo {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  margin-bottom: 8px;
}

.a2-apidoc-baseinfo .k {
  color: var(--a2-color-text-tertiary);
}

.a2-apidoc-baseinfo .v {
  margin-left: 8px;
  color: var(--a2-color-text-secondary);
}

.a2-apidoc-params {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.a2-apidoc-card {
  border: 1px solid var(--a2-color-border-secondary);
  border-radius: 6px;
}

.a2-apidoc-card-head {
  padding: 8px 12px;
  border-bottom: 1px solid var(--a2-color-border-secondary);
}

.a2-apidoc-card-body {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.a2-apidoc-resp-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 12px;
}

.a2-apidoc-resp-info .k {
  color: var(--a2-color-text-secondary);
}

:deep(.a2-param-line) {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.a2-param-name) {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  color: var(--a2-color-primary);
  background-color: rgba(255, 77, 79, 0.1);
  border-radius: 4px;
}

:deep(.a2-param-type) {
  font-weight: 600;
  color: var(--a2-color-text-secondary);
}

:deep(.a2-param-desc) {
  font-size: 12px;
  color: var(--a2-color-text-tertiary);
}

:deep(.a2-param-longdesc) {
  margin-top: 8px;
  font-size: 12px;
  color: var(--a2-color-text-tertiary);
}

:deep(.a2-param-example) {
  margin: 8px 0 0 4px;
  font-size: 12px;
}

:deep(.a2-param-example-val) {
  padding: 0 4px;
  color: var(--a2-color-text-tertiary);
  background-color: var(--a2-color-fill-tertiary);
  border: 1px solid var(--a2-color-border-secondary);
  border-radius: 4px;
}
</style>

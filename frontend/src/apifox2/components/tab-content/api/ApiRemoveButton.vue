<template>
  <el-popconfirm title="确定删除该接口？" placement="bottom" @confirm="onConfirm">
    <template #reference>
      <el-button>删除</el-button>
    </template>
  </el-popconfirm>
</template>

<script setup lang="ts">
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'
import { useApifox2TabStore } from '@/apifox2/stores/menuTab'

const props = defineProps<{ tabKey: string }>()

const menuStore = useApifox2MenuStore()
const tabStore = useApifox2TabStore()

function onConfirm() {
  tabStore.removeTabItem({ key: props.tabKey })
  menuStore.removeMenuItem({ id: props.tabKey })
}
</script>

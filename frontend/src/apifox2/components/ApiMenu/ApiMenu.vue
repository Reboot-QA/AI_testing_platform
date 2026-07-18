<template>
  <el-tree
    ref="treeRef"
    class="a2-menu-tree"
    node-key="key"
    :data="menuTree"
    :props="treeProps"
    :default-expanded-keys="expandedKeys"
    :expand-on-click-node="true"
    :indent="15"
    :draggable="true"
    :allow-drop="allowDrop"
    empty-text=""
    @node-click="onNodeClick"
    @node-drop="onNodeDrop"
  >
    <template #default="{ node, data }">
      <!-- 顶级目录标题 -->
      <div v-if="data.isTop" class="a2-node a2-node-top">
        <span class="a2-node-icon">
          <FolderIcon :type="data.catalogType" :size="15" />
        </span>
        <span class="a2-node-title">{{ topTitle(data) }}</span>
        <span
          v-if="!isNoActionTop(data.catalogType)"
          class="a2-caret"
          :class="{ expanded: node.expanded }"
        >
          <ChevronRightIcon :size="12" />
        </span>

        <span v-if="!isNoActionTop(data.catalogType)" class="a2-node-controls" @click.stop>
          <!-- 新建下拉 -->
          <el-dropdown
            trigger="click"
            placement="bottom-start"
            @command="(c: string) => onTopNew(data.catalogType, c)"
          >
            <MenuActionButton @click="(e: MouseEvent) => onTopCreate(data.catalogType, e)">
              <PlusIcon :size="14" />
            </MenuActionButton>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="newItem">
                  <FileIcon :type="data.catalogType" :size="14" class="a2-top-primary" />{{
                    topNewLabel(data.catalogType)
                  }}
                </el-dropdown-item>
                <el-dropdown-item command="newCatalog">
                  <FolderPlusIcon :size="14" class="a2-top-icon" />新建目录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>

          <!-- 全部展开/收起 -->
          <el-tooltip
            :content="isGroupAllExpanded(data.catalogType) ? '全部收起' : '全部展开'"
            placement="top"
          >
            <MenuActionButton @click="() => toggleExpandAll(data.catalogType)">
              <ChevronsDownUpIcon v-if="isGroupAllExpanded(data.catalogType)" :size="14" />
              <ChevronsUpDownIcon v-else :size="14" />
            </MenuActionButton>
          </el-tooltip>

          <!-- Http 显示模式 -->
          <el-dropdown
            v-if="data.catalogType === CatalogType.Http"
            trigger="click"
            placement="bottom-start"
            @command="onDisplayModeChange"
          >
            <MenuActionButton>
              <MoreHorizontalIcon :size="14" />
            </MenuActionButton>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="name">
                  <CheckIcon
                    :size="14"
                    class="a2-top-primary"
                    :style="{ opacity: menuStore.apiDetailDisplay === 'name' ? 1 : 0 }"
                  />接口显示为名称
                </el-dropdown-item>
                <el-dropdown-item command="path">
                  <CheckIcon
                    :size="14"
                    class="a2-top-primary"
                    :style="{ opacity: menuStore.apiDetailDisplay === 'path' ? 1 : 0 }"
                  />接口显示为 URL
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </span>
      </div>

      <!-- 普通节点（右键菜单） -->
      <DropdownActions
        v-else
        :catalog="data.catalog"
        :is-folder="!data.isLeaf"
        trigger="contextmenu"
        class="a2-node-dropdown"
      >
        <div class="a2-node">
          <span class="a2-node-icon">
            <template v-if="data.isLeaf">
              <span v-if="isHttpLike(data.catalog)" class="a2-method-wrap">
                <HttpMethodText :method="httpMethodOf(data.catalog)" />
              </span>
              <FileIcon
                v-else
                :type="data.catalog.type"
                :size="15"
                :style="fileIconStyle(data.catalog)"
              />
            </template>
            <template v-else>
              <FolderOpenIcon v-if="node.expanded" :size="14" />
              <FolderClosedIcon v-else :size="14" />
            </template>
          </span>

          <span class="a2-node-title">{{ nodeLabel(data) }}</span>
          <span v-if="!data.isLeaf && leafCount(data) > 0" class="a2-node-count"
            >({{ leafCount(data) }})</span
          >

          <!-- 悬浮控件 -->
          <span class="a2-node-controls" @click.stop>
            <template v-if="data.isLeaf">
              <DropdownActions :catalog="data.catalog" trigger="click">
                <MenuActionButton>
                  <MoreHorizontalIcon :size="14" />
                </MenuActionButton>
              </DropdownActions>
            </template>
            <template v-else>
              <el-tooltip :content="folderTip(data.catalog)" placement="top">
                <MenuActionButton @click="() => onFolderCreate(data.catalog)">
                  <PlusIcon :size="14" />
                </MenuActionButton>
              </el-tooltip>
              <DropdownActions :catalog="data.catalog" is-folder trigger="click">
                <MenuActionButton>
                  <MoreHorizontalIcon :size="14" />
                </MenuActionButton>
              </DropdownActions>
            </template>
          </span>
        </div>
      </DropdownActions>
    </template>
  </el-tree>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
  CheckIcon,
  ChevronRightIcon,
  ChevronsDownUpIcon,
  ChevronsUpDownIcon,
  FolderClosedIcon,
  FolderOpenIcon,
  FolderPlusIcon,
  MoreHorizontalIcon,
  PlusIcon,
} from 'lucide-vue-next'
import FileIcon from '@/apifox2/components/icons/FileIcon.vue'
import FolderIcon from '@/apifox2/components/icons/FolderIcon.vue'
import HttpMethodText from '@/apifox2/components/icons/HttpMethodText.vue'
import MenuActionButton from './MenuActionButton.vue'
import DropdownActions from './DropdownActions.vue'
import { API_MENU_CONFIG, ROOT_CATALOG } from '@/apifox2/configs/static'
import { CatalogType, HttpMethod, MenuItemType } from '@/apifox2/enums'
import {
  getCatalogType,
  getCreateType,
  hasAccentColor,
  isMenuFolder,
  isMenuSameGroup,
} from '@/apifox2/helpers'
import { PageTabStatus } from '@/apifox2/components/ApiTab/ApiTab.enum'
import { initialExpandedKeys } from '@/apifox2/data/remote'
import type { ApiMenuData } from '@/apifox2/components/ApiMenu'
import type { TabContentType } from '@/apifox2/types'
import { useMenuData, type MenuTreeNode } from '@/apifox2/composables/useMenuData'
import { useHelpers } from '@/apifox2/composables/useHelpers'
import { useApifox2NewCatalog } from '@/apifox2/composables/useModals'
import { useApifox2MenuStore } from '@/apifox2/stores/menuHelpers'
import { useApifox2TabStore } from '@/apifox2/stores/menuTab'

const { menuTree } = useMenuData()
const menuStore = useApifox2MenuStore()
const tabStore = useApifox2TabStore()
const { createTabItem } = useHelpers()
const { openNewCatalog } = useApifox2NewCatalog()

const treeRef = ref()
const expandedKeys = ref<string[]>([...initialExpandedKeys])

const treeProps = { children: 'children', label: 'key' }

// —— 节点渲染 ——
function isHttpLike(catalog: ApiMenuData): boolean {
  return catalog.type === MenuItemType.ApiDetail || catalog.type === MenuItemType.HttpRequest
}
function httpMethodOf(catalog: ApiMenuData): HttpMethod | undefined {
  if (catalog.type === MenuItemType.ApiDetail || catalog.type === MenuItemType.HttpRequest) {
    return catalog.data?.method
  }
  return undefined
}
function fileIconStyle(catalog: ApiMenuData) {
  const { accentColor } = API_MENU_CONFIG[getCatalogType(catalog.type)]
  return { color: hasAccentColor(catalog.type) ? accentColor : undefined }
}
function nodeLabel(data: MenuTreeNode): string {
  const catalog = data.catalog
  if (!catalog) return ''
  if (catalog.type === MenuItemType.ApiDetail) {
    return menuStore.apiDetailDisplay === 'name'
      ? catalog.name
      : (catalog.data?.path ?? catalog.name)
  }
  return catalog.name
}
function leafCount(data: MenuTreeNode): number {
  let count = 0
  data.children?.forEach((child) => {
    if (child.isLeaf) count += 1
    else count += leafCount(child)
  })
  return count
}
function topTitle(data: MenuTreeNode): string {
  return data.catalogType ? API_MENU_CONFIG[data.catalogType].title : ''
}
function topNewLabel(ct?: CatalogType): string {
  return ct ? API_MENU_CONFIG[ct].newLabel : ''
}
function isNoActionTop(ct?: CatalogType): boolean {
  return ct === CatalogType.Overview || ct === CatalogType.Recycle
}
function folderTip(catalog: ApiMenuData): string {
  return API_MENU_CONFIG[getCatalogType(catalog.type)].tipTitle
}

// —— 交互 ——
function onNodeClick(data: MenuTreeNode) {
  if (data.isTop && data.catalogType) {
    if (data.catalogType === CatalogType.Overview || data.catalogType === CatalogType.Recycle) {
      openTab(data.catalogType, API_MENU_CONFIG[data.catalogType].title, data.catalogType)
    }
    return
  }
  const catalog = data.catalog
  if (!catalog) return

  const isTabPresent = tabStore.tabItems.some(({ key }) => key === catalog.id)
  if (isTabPresent) {
    tabStore.activeTabItem({ key: catalog.id })
    return
  }

  if (
    catalog.type !== MenuItemType.ApiSchemaFolder &&
    catalog.type !== MenuItemType.RequestFolder
  ) {
    tabStore.addTabItem({
      key: catalog.id,
      label: catalog.name,
      contentType: catalog.type,
      data: { tabStatus: PageTabStatus.Update },
    })
  }
}

function openTab(key: string, label: string, contentType: TabContentType) {
  const existing = tabStore.getTabItem({ key })
  if (existing) {
    tabStore.activeTabItem({ key })
    return
  }
  tabStore.addTabItem({ key, label, contentType })
}

function onFolderCreate(catalog: ApiMenuData) {
  createTabItem(getCreateType(catalog.type))
}

function onTopCreate(ct: CatalogType | undefined, e: MouseEvent) {
  e.stopPropagation()
  if (ct) createTabItem(getCreateType(ct))
}

function onTopNew(ct: CatalogType | undefined, command: string) {
  if (!ct) return
  if (command === 'newItem') {
    createTabItem(getCreateType(ct))
  } else if (command === 'newCatalog') {
    const type =
      ct === CatalogType.Http
        ? MenuItemType.ApiDetailFolder
        : ct === CatalogType.Schema
          ? MenuItemType.ApiSchemaFolder
          : MenuItemType.RequestFolder
    openNewCatalog({ parentId: ROOT_CATALOG, type })
  }
}

function onDisplayModeChange(command: string) {
  menuStore.setApiDetailDisplay(command === 'path' ? 'path' : 'name')
}

// —— 展开/收起 ——
function groupFolderKeys(ct?: CatalogType): string[] {
  if (!ct) return []
  const keys: string[] = [ct]
  menuStore.menuRawList?.forEach((it) => {
    if (isMenuFolder(it.type) && getCatalogType(it.type) === ct) {
      keys.push(it.id)
    }
  })
  return keys
}

function isGroupAllExpanded(ct?: CatalogType): boolean {
  const keys = groupFolderKeys(ct)
  return keys.every((key) => {
    const node = treeRef.value?.getNode(key)
    return node ? node.expanded : false
  })
}

function toggleExpandAll(ct?: CatalogType) {
  const keys = groupFolderKeys(ct)
  const expand = !isGroupAllExpanded(ct)
  keys.forEach((key) => {
    const node = treeRef.value?.getNode(key)
    if (node) node.expanded = expand
  })
}

// —— 拖拽 ——
function allowDrop(
  draggingNode: { data: MenuTreeNode },
  dropNode: { data: MenuTreeNode },
  type: string,
) {
  if (dropNode.data.isTop) return false
  const dragCatalog = draggingNode.data.catalog
  const dropCatalog = dropNode.data.catalog
  if (!dragCatalog || !dropCatalog) return false
  if (type === 'inner' && dropNode.data.isLeaf) return false
  return isMenuSameGroup(dragCatalog, dropCatalog)
}

function onNodeDrop(
  draggingNode: { data: MenuTreeNode },
  dropNode: { data: MenuTreeNode },
  dropType: string,
) {
  const dragKey = draggingNode.data.catalog?.id
  const dropKey = dropNode.data.catalog?.id
  if (!dragKey || !dropKey) return
  const dropPosition = dropType === 'inner' ? 0 : dropType === 'after' ? 1 : -1
  menuStore.moveMenuItem({ dragKey, dropKey, dropPosition })
}
</script>

<style scoped>
.a2-menu-tree {
  background: transparent;
  --el-tree-node-hover-bg-color: var(--a2-color-fill-tertiary);
}

.a2-node {
  display: flex;
  align-items: center;
  width: 100%;
  overflow: hidden;
  gap: 4px;
}

.a2-node-dropdown {
  width: 100%;
  overflow: hidden;
}

.a2-node-top {
  color: var(--a2-color-text-secondary);
  font-weight: 500;
}

.a2-node-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.a2-method-wrap {
  display: inline-block;
  width: 29px;
  white-space: nowrap;
  text-align: left;
  font-size: 12px;
  line-height: 1;
  font-weight: 600;
}

.a2-node-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.a2-node-count {
  font-size: 12px;
  color: var(--a2-color-text-tertiary);
  flex-shrink: 0;
}

.a2-caret {
  display: inline-flex;
  transition: transform 0.15s;
  flex-shrink: 0;
  color: var(--a2-color-text-tertiary);
}

.a2-caret.expanded {
  transform: rotate(90deg);
}

.a2-node-controls {
  margin-left: auto;
  display: none;
  align-items: center;
  white-space: nowrap;
  flex-shrink: 0;
}

.a2-node:hover .a2-node-controls,
.a2-node-top:hover .a2-node-controls {
  display: inline-flex;
}

.a2-top-primary {
  margin-right: 6px;
  color: var(--a2-color-primary);
}

.a2-top-icon {
  margin-right: 6px;
}
</style>

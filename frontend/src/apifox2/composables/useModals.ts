import { reactive } from 'vue'

import type { ApiMenuData } from '@/apifox2/components/ApiMenu'
import type { MenuItemType } from '@/apifox2/enums'

interface NewCatalogState {
  visible: boolean
  type?: MenuItemType
  parentId?: ApiMenuData['parentId']
}

interface RenameState {
  visible: boolean
  id?: string
  name?: string
}

interface MoveMenuState {
  visible: boolean
  id?: string
  parentId?: ApiMenuData['parentId']
  menuItemType?: MenuItemType
}

interface SettingsState {
  visible: boolean
  selectedKey?: string
}

interface ModalsState {
  newCatalog: NewCatalogState
  rename: RenameState
  moveMenu: MoveMenuState
  settings: SettingsState
}

// 模块级单例，供 ModalsHost 与任意触发方共享。
const state = reactive<ModalsState>({
  newCatalog: { visible: false },
  rename: { visible: false },
  moveMenu: { visible: false },
  settings: { visible: false },
})

export function useApifox2Modals() {
  return { state }
}

export function useApifox2NewCatalog() {
  return {
    openNewCatalog(formData?: Pick<ApiMenuData, 'parentId' | 'type'>) {
      state.newCatalog.visible = true
      state.newCatalog.type = formData?.type
      state.newCatalog.parentId = formData?.parentId
    },
  }
}

export function useApifox2Rename() {
  return {
    openRename(formData: { id: string; name?: string }) {
      state.rename.visible = true
      state.rename.id = formData.id
      state.rename.name = formData.name
    },
  }
}

export function useApifox2MoveMenu() {
  return {
    openMoveMenu(
      formData: { id: string; parentId?: ApiMenuData['parentId'] },
      menuItemType?: MenuItemType,
    ) {
      state.moveMenu.visible = true
      state.moveMenu.id = formData.id
      state.moveMenu.parentId = formData.parentId
      state.moveMenu.menuItemType = menuItemType
    },
  }
}

export function useApifox2Settings() {
  return {
    openSettings(selectedKey?: string) {
      state.settings.visible = true
      state.settings.selectedKey = selectedKey
    },
  }
}

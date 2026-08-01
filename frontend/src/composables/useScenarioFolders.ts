// 场景文件夹（单层分组）：状态 + 增删改，封装弹窗与 API。pidRef 为项目 id 的响应式引用。
import { ref, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'
import type { Schemas } from '@/api/types'
import { nameInputOptions } from '@/utils/promptLimits'

type ScenarioFolder = Schemas['ScenarioFolderOut']

export function useScenarioFolders(pidRef: Ref<number | string | null | undefined>) {
  const folders = ref<ScenarioFolder[]>([])

  async function loadFolders(): Promise<void> {
    folders.value = await apifoxApi.listScenarioFolders(pidRef.value!)
  }

  async function createFolder(): Promise<ScenarioFolder | null> {
    const { value } = await ElMessageBox.prompt('文件夹名称', '新建场景文件夹', {
      ...nameInputOptions(),
    })
    const created = await apifoxApi.createScenarioFolder(pidRef.value!, value.trim())
    ElMessage.success('已创建')
    await loadFolders()
    return created
  }

  async function renameFolder(folder: ScenarioFolder): Promise<void> {
    const { value } = await ElMessageBox.prompt('文件夹名称', '重命名', {
      inputValue: folder.name,
      ...nameInputOptions(),
    })
    await apifoxApi.renameScenarioFolder(folder.id, value.trim())
    ElMessage.success('已重命名')
    await loadFolders()
  }

  async function deleteFolder(folder: ScenarioFolder): Promise<void> {
    await ElMessageBox.confirm(
      `删除文件夹「${folder.name}」？文件夹中的场景会被一起删除（可在回收站还原）。`,
      '删除文件夹',
      { type: 'warning' },
    )
    await apifoxApi.deleteScenarioFolder(folder.id)
    ElMessage.success('已删除')
    await loadFolders()
  }

  return { folders, loadFolders, createFolder, renameFolder, deleteFolder }
}

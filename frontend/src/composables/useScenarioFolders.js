// 场景文件夹（单层分组）：状态 + 增删改，封装弹窗与 API。pidRef 为项目 id 的响应式引用。
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { apifoxApi } from '@/api'

export function useScenarioFolders(pidRef) {
  const folders = ref([])

  async function loadFolders() {
    folders.value = await apifoxApi.listScenarioFolders(pidRef.value)
  }

  async function createFolder() {
    const { value } = await ElMessageBox.prompt('文件夹名称', '新建场景文件夹', {
      inputPattern: /\S/,
      inputErrorMessage: '不能为空',
    })
    await apifoxApi.createScenarioFolder(pidRef.value, value.trim())
    ElMessage.success('已创建')
    await loadFolders()
  }

  async function renameFolder(folder) {
    const { value } = await ElMessageBox.prompt('文件夹名称', '重命名', {
      inputValue: folder.name,
      inputPattern: /\S/,
      inputErrorMessage: '不能为空',
    })
    await apifoxApi.renameScenarioFolder(folder.id, value.trim())
    ElMessage.success('已重命名')
    await loadFolders()
  }

  async function deleteFolder(folder) {
    await ElMessageBox.confirm(
      `删除文件夹「${folder.name}」？其下场景会移到未分组（不会删除场景）。`,
      '删除文件夹',
      { type: 'warning' },
    )
    await apifoxApi.deleteScenarioFolder(folder.id)
    ElMessage.success('已删除')
    await loadFolders()
  }

  return { folders, loadFolders, createFolder, renameFolder, deleteFolder }
}

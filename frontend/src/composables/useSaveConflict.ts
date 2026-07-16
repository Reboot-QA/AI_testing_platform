import { ElMessage, ElMessageBox } from 'element-plus'

interface SaveConflictHandlers {
  /** 拉取最新并覆盖本地表单 */
  reload: () => Promise<unknown>
  /** 刷新版本号后用本地内容强制保存 */
  overwrite: () => Promise<unknown>
}

export type DirtyAction = 'save' | 'discard' | 'cancel'

// 乐观锁保存冲突(HTTP 409)统一处理：他人已先保存，本地改动尚未落库。
// 让用户在「加载最新(丢弃本地)」与「覆盖保存(用本地覆盖对方)」之间选择。
export async function resolveSaveConflict({
  reload,
  overwrite,
}: SaveConflictHandlers): Promise<void> {
  // 先只用弹窗决定动作，不把 reload/overwrite 的运行时异常混进 action 判断
  let action: 'reload' | 'cancel' | 'close'
  try {
    await ElMessageBox.confirm(
      '该内容已被他人修改，你的改动尚未保存。请选择如何处理：',
      '保存冲突',
      {
        confirmButtonText: '加载最新（放弃我的改动）',
        cancelButtonText: '覆盖保存（用我的改动）',
        distinguishCancelAndClose: true,
        type: 'warning',
      },
    )
    action = 'reload'
  } catch (signal) {
    // 'cancel'（覆盖保存）| 'close'（ESC/关闭，保持现状）
    action = signal as 'cancel' | 'close'
  }

  if (action === 'reload') {
    try {
      await reload()
      ElMessage.info('已加载最新版本')
    } catch {
      ElMessage.error('加载最新版本失败，请重试')
    }
  } else if (action === 'cancel') {
    try {
      await overwrite()
      ElMessage.success('已覆盖保存')
    } catch (e) {
      ElMessage.error(isConflict(e) ? '覆盖失败：又被他人修改，请重试' : '覆盖保存失败，请重试')
    }
  }
  // 'close'/ESC：保持现状，用户可继续编辑后再存
}

// 判断是否为乐观锁冲突错误
export function isConflict(err: unknown): boolean {
  return (err as { response?: { status?: number } } | null)?.response?.status === 409
}

// 未保存改动确认弹窗底座：返回 'save' | 'discard' | 'cancel'（close/ESC 视为 cancel，避免误操作丢改动）。
async function _confirmDirty(
  question: string,
  confirmText: string,
  cancelText: string,
): Promise<DirtyAction> {
  try {
    await ElMessageBox.confirm(question, '未保存的改动', {
      confirmButtonText: confirmText,
      cancelButtonText: cancelText,
      distinguishCancelAndClose: true,
      type: 'warning',
    })
    return 'save'
  } catch (signal) {
    return signal === 'cancel' ? 'discard' : 'cancel'
  }
}

// 关闭有未保存改动的编辑 tab
export function confirmCloseDirty(tabName: string): Promise<DirtyAction> {
  return _confirmDirty(`「${tabName}」有未保存的改动，关闭前要保存吗？`, '保存并关闭', '不保存关闭')
}

// 离开有未保存改动的编辑对象（切换/离开）
export function confirmUnsaved(name: string): Promise<DirtyAction> {
  return _confirmDirty(`「${name}」有未保存的改动，是否保存？`, '保存', '不保存')
}

import { ElMessage, ElMessageBox } from 'element-plus'

// 乐观锁保存冲突(HTTP 409)统一处理：他人已先保存，本地改动尚未落库。
// 让用户在「加载最新(丢弃本地)」与「覆盖保存(用本地覆盖对方)」之间选择。
//   reload:    () => Promise  拉取最新并覆盖本地表单
//   overwrite: () => Promise  刷新版本号后用本地内容强制保存
export async function resolveSaveConflict({ reload, overwrite }) {
  // 先只用弹窗决定动作，不把 reload/overwrite 的运行时异常混进 action 判断
  let action
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
    action = signal // 'cancel'（覆盖保存）| 'close'（ESC/关闭，保持现状）
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
export function isConflict(err) {
  return err?.response?.status === 409
}

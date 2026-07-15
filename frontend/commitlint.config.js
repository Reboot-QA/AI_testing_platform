// commit message 校验：中文 conventional commits（如 `feat(apifox): 新增场景步骤拖拽`）
export default {
  extends: ['@commitlint/config-conventional'],
  rules: {
    // 中文 subject 不做大小写限制；header 长度放宽到 100
    'subject-case': [0],
    'header-max-length': [2, 'always', 100],
  },
}

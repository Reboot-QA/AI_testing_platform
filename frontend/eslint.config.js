// ESLint flat config（规则依据《前端开发规范（Vue）v1.0》）
// 原则：新代码严格；存量不可自动修复项降为 warn，保证基线 0 error。
import pluginVue from 'eslint-plugin-vue'
import eslintConfigPrettier from 'eslint-config-prettier'
import tsParser from '@typescript-eslint/parser'
import globals from 'globals'

export default [
  {
    ignores: ['node_modules/**', 'dist/**', '**/*.d.ts'],
  },
  ...pluginVue.configs['flat/recommended'],
  // TS 文件与 <script lang="ts"> 的解析支持（渐进式 TS 迁移）
  {
    files: ['**/*.ts'],
    languageOptions: { parser: tsParser },
  },
  {
    files: ['**/*.vue'],
    languageOptions: { parserOptions: { parser: { ts: tsParser } } },
  },
  {
    files: ['**/*.{js,ts,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // 规范 v1.0 §2.3：禁 var、优先 const
      'no-var': 'error',
      'prefer-const': 'error',
      // 规范 v1.0 §5.4：v-for 必须 key；v-if 不与 v-for 同元素
      'vue/require-v-for-key': 'error',
      'vue/no-use-v-if-with-v-for': 'error',
      // 项目页面组件多为单词名（Requirements、Dashboard 等），关闭多词限制
      'vue/multi-word-component-names': 'off',
      // 存量代码基线：不可自动修复项降级为 warn，新代码应消除
      'no-unused-vars': ['warn', { args: 'none' }],
      'vue/no-unused-vars': 'warn',
      'vue/require-default-prop': 'warn',
      'vue/require-prop-types': 'warn',
      // 存量技术债（106 处 prop 直改 + 2 处 computed 副作用，集中在旧模块表格组件）：
      // 降为 warn 保证基线 0 error；新代码严禁新增，改动相关文件时应顺手偿还
      'vue/no-mutating-props': 'warn',
      'vue/no-side-effects-in-computed-properties': 'warn',
    },
  },
  // 关闭与 Prettier 冲突的格式类规则（必须放最后）
  eslintConfigPrettier,
]

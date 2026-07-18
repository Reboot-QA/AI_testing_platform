import { computed, reactive } from 'vue'

import {
  defaultThemeSetting,
  larkPrimary,
  type ThemeSetting,
} from '@/apifox2/components/ThemeEditor/theme-data'

const STORAGE_KEY = 'apifox2-theme-setting'

function restore(): ThemeSetting {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (raw) return { ...defaultThemeSetting, ...(JSON.parse(raw) as ThemeSetting) }
  } catch {
    // ignore
  }
  return { ...defaultThemeSetting }
}

// 模块级单例，供 ApifoxLayout 应用、ThemeEditor 修改。
const themeSetting = reactive<ThemeSetting>(restore())

export function useApifox2Theme() {
  const isDarkMode = computed(() => themeSetting.themeMode === 'darkDefault')

  /** 实际生效的主色：lark 固定绿色，默认主题用 colorPrimary。 */
  const effectivePrimary = computed(() =>
    themeSetting.themeMode === 'lark' ? larkPrimary : themeSetting.colorPrimary,
  )

  /** 绑定到 .apifox2-root 的 data-theme 属性。 */
  const dataTheme = computed(() => themeSetting.themeMode)

  /** 绑定到 .apifox2-root 的内联 CSS 变量。 */
  const rootStyle = computed(() => ({
    '--a2-color-primary': effectivePrimary.value,
    '--a2-radius': `${themeSetting.borderRadius}px`,
  }))

  function setThemeSetting(value: Partial<ThemeSetting>) {
    Object.assign(themeSetting, value)
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(themeSetting))
    } catch {
      // ignore
    }
  }

  return { themeSetting, isDarkMode, dataTheme, rootStyle, setThemeSetting }
}

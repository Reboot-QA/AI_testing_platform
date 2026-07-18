export type ThemeMode = 'lightDefault' | 'darkDefault' | 'lark'

export interface ThemeSetting {
  themeMode: ThemeMode
  colorPrimary: string
  borderRadius: number
  spaceType: 'default' | 'compact'
}

export const defaultThemeSetting: ThemeSetting = {
  themeMode: 'lightDefault',
  colorPrimary: '#1677ff',
  borderRadius: 6,
  spaceType: 'default',
}

/** 预设主题元信息（preview 用 CSS mock 卡片近似参考项目的 SVG 缩略图）。 */
export const presetThemes: Record<ThemeMode, { name: string; previewClass: string }> = {
  lightDefault: { name: '默认', previewClass: 'preview-light' },
  darkDefault: { name: '暗黑', previewClass: 'preview-dark' },
  lark: { name: '知识协作', previewClass: 'preview-lark' },
}

export const presetRadius: number[] = [2, 4, 6]

export const presetColors: string[] = [
  '#1677ff',
  '#9373ee',
  '#5f80e9',
  '#587df1',
  '#9a7d56',
  '#039e74',
  '#e86ca4',
  '#fd6874',
  '#8e8374',
]

/** lark 主题主色。 */
export const larkPrimary = '#00b96b'

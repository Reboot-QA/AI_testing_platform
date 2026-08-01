export default {
  overrides: [
    {
      files: ['**/*.vue', '**/*.css'],
      customSyntax: 'postcss-html',
    },
  ],
  ignoreFiles: ['src/styles/tokens.css'],
  rules: {
    'color-no-hex': true,
    'function-disallowed-list': ['rgb', 'rgba', 'hsl', 'hsla'],
  },
}

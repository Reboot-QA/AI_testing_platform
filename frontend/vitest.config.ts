import { defineConfig } from 'vitest/config'
import { fileURLToPath, URL } from 'node:url'

// 独立于 vite.config.ts：不复用 monaco manualChunks 与 dev proxy
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'node',
    include: ['tests/**/*.spec.ts'],
    coverage: {
      provider: 'v8',
      reportsDirectory: './coverage',
      include: [
        'src/utils/curlParser.ts',
        'src/utils/caseProcessors.ts',
        'src/utils/assertionItems.ts',
        'src/utils/runReportStats.ts',
        'src/utils/scenarioSteps.ts',
        'src/utils/scenarioStepFactory.ts',
        'src/utils/importPreviewTree.ts',
        'src/utils/httpHeaders.ts',
        'src/utils/datetime.ts',
        'src/composables/useSuiteItemGroups.ts',
        'src/composables/useJsonSchema.ts',
        'src/composables/useScheduleTargetTree.ts',
        'src/composables/useRequirementDisplay.ts',
        'src/composables/useTestExecutionDisplay.ts',
        'src/composables/useTableFilter.ts',
        'src/composables/useScenarioPriority.ts',
      ],
    },
  },
})

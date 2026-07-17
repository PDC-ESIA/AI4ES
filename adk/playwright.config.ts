import { defineConfig, devices } from '@playwright/test';

const testDir = process.env.E2E_TEST_DIR ?? './workspace_output/tests/e2e';
const testMatch = process.env.E2E_SPEC_NAME ?? '**/*.spec.ts';
const outputDir =
  process.env.E2E_ARTIFACTS_DIR ?? './workspace_output/tests/e2e/test-results';
const reportFile =
  process.env.PLAYWRIGHT_JSON_OUTPUT_FILE ??
  './workspace_output/tests/e2e/playwright-report.json';
const timeout = Number(process.env.E2E_TEST_TIMEOUT_MS ?? '30000');
const globalTimeout = Number(process.env.E2E_GLOBAL_TIMEOUT_MS ?? '120000');

export default defineConfig({
  testDir,
  testMatch,
  outputDir,
  timeout,
  globalTimeout,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: true,
  reporter: [['json', { outputFile: reportFile }]],
  use: {
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});

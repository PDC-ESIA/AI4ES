const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: '/work/suite', testMatch: process.env.QA_SPEC,
  outputDir: '/tmp/results', workers: 1, retries: 0, forbidOnly: true,
  timeout: 30000, globalTimeout: 120000,
  reporter: [['json', { outputFile: '/tmp/playwright.json' }]],
  use: { headless: true, trace: 'off', screenshot: 'off', video: 'off' },
});

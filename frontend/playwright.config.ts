import { defineConfig } from '@playwright/test';
import type { Project } from '@playwright/test';
import { resolve } from 'node:path';

const reports = process.env.RUNNER_TEMP
  ? resolve(process.env.RUNNER_TEMP, 'goalguard-browser')
  : resolve(import.meta.dirname, '../.local/checks/browser');

const reviewProjects: Project[] = [
  { name: 'review-tablet', use: { browserName: 'chromium', viewport: { width: 768, height: 1024 } } },
  { name: 'review-breakpoint', use: { browserName: 'chromium', viewport: { width: 801, height: 900 } } },
  { name: 'review-laptop', use: { browserName: 'chromium', viewport: { width: 1024, height: 768 } } },
  // 320 CSS px models reflow of a 1280px-wide viewport at 400%; not native browser zoom.
  { name: 'review-reflow', use: { browserName: 'chromium', viewport: { width: 320, height: 256 } } },
  { name: 'review-text', metadata: { textPreference: true }, use: { browserName: 'chromium', viewport: { width: 1280, height: 900 } } },
  { name: 'review-firefox-desktop', use: { browserName: 'firefox', viewport: { width: 1024, height: 768 } } },
  { name: 'review-firefox-phone', use: { browserName: 'firefox', viewport: { width: 375, height: 900 } } },
  { name: 'review-webkit-desktop', use: { browserName: 'webkit', viewport: { width: 1024, height: 768 } } },
  { name: 'review-webkit-phone', use: { browserName: 'webkit', viewport: { width: 375, height: 900 } } },
].map(project => ({ ...project, testMatch: '**/review.spec.ts' }));

export default defineConfig({
  testDir: './tests/browser',
  outputDir: resolve(reports, 'results'),
  reporter: [['list'], ['json', { outputFile: resolve(reports, 'results.json') }],
    ['html', { outputFolder: resolve(reports, 'report'), open: 'never' }]],
  updateSnapshots: 'none',
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 5_000, toHaveScreenshot: { animations: 'disabled', maxDiffPixels: 0 } },
  use: {
    baseURL: 'http://127.0.0.1:5189',
    browserName: 'chromium',
    locale: 'en-US', timezoneId: 'UTC', reducedMotion: 'reduce',
    serviceWorkers: 'block', acceptDownloads: false,
    trace: 'retain-on-failure', screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', testIgnore: '**/review.spec.ts', use: { viewport: { width: 1440, height: 1000 } } },
    { name: 'phone', testIgnore: '**/review.spec.ts', use: { viewport: { width: 375, height: 900 } } },
    { name: 'narrow', testIgnore: '**/review.spec.ts', use: { viewport: { width: 320, height: 900 } } },
    ...reviewProjects,
  ],
  // Never attach to a developer's owner server or reuse its cookies/data.
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 5189 --strictPort',
    url: 'http://127.0.0.1:5189', reuseExistingServer: false,
  },
});

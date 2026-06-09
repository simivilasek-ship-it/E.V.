import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 30_000,

  use: {
    baseURL: process.env.JARVIS_BASE_URL || 'http://localhost:8002',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'python3 dashboard.py',
    url: 'http://localhost:8002/api/health',
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
    cwd: '..',
    env: {
      JARVIS_TEST_MODE: '1',
      JARVIS_BIND_HOST: '0.0.0.0',
      JARVIS_API_AUTH_REQUIRED: '0',
    },
  },
});

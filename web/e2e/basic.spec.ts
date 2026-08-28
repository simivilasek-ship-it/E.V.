import { test, expect } from '@playwright/test';

/**
 * Full-stack E2E tests for E.V..
 * Runs against the Python backend (dashboard.py) on port 8002.
 * Backend is started automatically via playwright.config.ts webServer.
 */

test.describe('E.V. — full-stack E2E', () => {

  test('page loads E.V. UI', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('domcontentloaded');

    // Root app container should be present
    const app = page.locator('[data-testid="ev-app"]');
    await expect(app).toBeVisible({ timeout: 15_000 });
  });

  test('sidebar is visible with navigation items', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    const sidebar = page.locator('[data-testid="sidebar"]');
    await expect(sidebar).toBeVisible();

    // At minimum Chat nav item should exist
    const chatNav = page.locator('[data-testid="nav-item-chat"]');
    await expect(chatNav).toBeVisible();
  });

  test('home core is visible and chat opens from the corner', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[data-testid="home-stage"]')).toBeVisible();
    await expect(page.locator('[data-testid="open-chat"]')).toBeVisible();
    await page.locator('[data-testid="open-chat"]').click();

    const input = page.locator('[data-testid="chat-input"]');
    await expect(input).toBeVisible();
    await expect(input).toBeEnabled();
    await input.click();
    await input.fill('test message');
    await expect(input).toHaveValue('test message');
    await input.fill('');
  });

  test('API health endpoint returns ok', async ({ request }) => {
    const res = await request.get('http://localhost:8002/api/health');
    expect(res.ok()).toBeTruthy();

    const body = await res.json();
    // Backend should report some form of status
    expect(body).toHaveProperty('status');
    expect(['ok', 'degraded', 'healthy']).toContain(body.status);
  });

  test('work timeline panel loads (may be empty in test mode)', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    // Open the advanced section and navigate to Work/Timeline
    const advancedBtn = page.locator('button', { hasText: 'Pokročilé' });
    if (await advancedBtn.isVisible()) {
      await advancedBtn.click();
    }

    const workNav = page.locator('[data-testid="nav-item-work"]');
    if (await workNav.isVisible()) {
      await workNav.click();
      // Panel should load (either content or empty-state message)
      await page.waitForTimeout(500);
      const pageContent = await page.content();
      expect(pageContent.length).toBeGreaterThan(500);
    } else {
      // Fallback: just confirm the app is rendered
      await expect(page.locator('[data-testid="ev-app"]')).toBeVisible();
    }
  });

  test('settings panel opens when clicking Settings in sidebar', async ({ page }) => {
    await page.goto('/app');
    await page.waitForLoadState('networkidle');

    // Open the advanced section to reveal Settings
    const advancedBtn = page.locator('button', { hasText: 'Pokročilé' });
    if (await advancedBtn.isVisible()) {
      await advancedBtn.click();
    }

    const settingsNav = page.locator('[data-testid="nav-item-settings"]');
    await expect(settingsNav).toBeVisible();
    await settingsNav.click();

    // Settings panel content should appear (e.g. a heading)
    await page.waitForTimeout(500);
    const pageText = await page.textContent('body');
    expect(pageText).toBeTruthy();
    // Settings panel typically has the word "Nastavení" or "Settings"
    const hasSettingsContent =
      pageText?.includes('Nastavení') ||
      pageText?.includes('model') ||
      pageText?.includes('TTS') ||
      pageText?.includes('settings');
    expect(hasSettingsContent).toBeTruthy();
  });

  test('no JavaScript console errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => {
      // Ignore known non-critical browser/library noise
      if (
        !err.message.includes('ResizeObserver') &&
        !err.message.includes('Non-Error promise rejection') &&
        !err.message.includes('WebSocket') &&
        !err.message.includes('favicon')
      ) {
        errors.push(err.message);
      }
    });

    await page.goto('/app', { waitUntil: 'domcontentloaded', timeout: 20_000 });
    // Give the page a moment to trigger any synchronous errors
    await page.waitForTimeout(1000);

    expect(errors).toHaveLength(0);
  });

});

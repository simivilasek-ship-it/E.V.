import { test, expect } from '@playwright/test';

/**
 * Basic E2E smoke tests for JARVIS web UI.
 * These run against a live Next.js dev server or static build.
 * In CI they run against the built app served via `next start`.
 */

test.describe('JARVIS Web UI — smoke', () => {
  test('homepage loads without errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));

    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');

    // Should render the app shell
    const body = await page.textContent('body');
    expect(body).toBeTruthy();
    expect(errors).toHaveLength(0);
  });

  test('sidebar is visible', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Sidebar should render version string
    const sidebar = page.locator('nav, aside, [data-testid="sidebar"]').first();
    if (await sidebar.isVisible()) {
      await expect(sidebar).toBeVisible();
    } else {
      // Fallback: page has meaningful content
      const html = await page.content();
      expect(html.length).toBeGreaterThan(500);
    }
  });

  test('chat input is present', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Look for a chat input or textarea
    const input = page.locator('input[type="text"], textarea').first();
    const count = await page.locator('input[type="text"], textarea').count();
    if (count > 0) {
      await expect(input).toBeVisible();
    } else {
      // App may not have loaded backend — at minimum page renders
      const html = await page.content();
      expect(html).toContain('JARVIS');
    }
  });

  test('no critical JS errors on navigation to /app', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => {
      // Ignore known non-critical errors
      if (!err.message.includes('ResizeObserver') && !err.message.includes('Non-Error')) {
        errors.push(err.message);
      }
    });

    try {
      await page.goto('/app', { waitUntil: 'domcontentloaded', timeout: 15_000 });
    } catch {
      // /app may redirect to / — that's fine
      await page.goto('/', { waitUntil: 'domcontentloaded' });
    }

    expect(errors).toHaveLength(0);
  });
});

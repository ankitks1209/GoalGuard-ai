import AxeBuilder from '@axe-core/playwright';
import { test, expect, openWorkspace, overview, instant } from './fixtures';
import type { Page, TestInfo } from '@playwright/test';

async function checkTimeline(page: Page, info: TestInfo) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  await info.attach('timeline-axe-results', { body: JSON.stringify(result, null, 2), contentType: 'application/json' });
  expect(result.violations.map(item => item.id)).toEqual([]);
}

for (const state of ['empty', 'loading', 'error', 'offline'] as const) {
  test.describe(`timeline state ${state}`, () => {
    test.use({ scenario: state });
    test('distinguishes known empty history from unread data', async ({ page, scenario }, info) => {
      await openWorkspace(page, scenario);
      await page.getByRole('button', { name: 'Timeline', exact: true }).click();
      await expect(page.getByRole('heading', { name: 'Your timeline', exact: true })).toHaveCount(1);
      if (state === 'empty') {
        await expect(page.getByRole('heading', { name: 'A fresh start' })).toBeVisible();
      } else {
        await expect(page.getByRole('heading', { name: 'A fresh start' })).toHaveCount(0);
        if (state === 'loading') await expect(page.getByRole('status')).toHaveText('Loading your timeline…');
        else await expect(page.getByText('Timeline is unavailable. Refresh workspace to read current status.')).toBeVisible();
      }
      await checkTimeline(page, info);
      await expect(page).toHaveScreenshot(`timeline-${state}.png`, { fullPage: true });
    });
  });
}

test('keeps every recorded event, reference and timestamp in server order through a read-only refresh', async ({ page, scenario }, info) => {
  const data = overview('ready');
  const at = instant.getTime() / 1000;
  const longReference = 'synthetic-purchase-with-an-unusually-long-unbroken-reference-for-reflow';
  data.events = [
    { id: 'synthetic-4', at: at + 720, event: 'approved', purchase_id: 'synthetic-cart-001', details: {} },
    { id: 'synthetic-3', at: at + 600, event: 'reserved', purchase_id: 'synthetic-cart-001', details: {} },
    { id: 'synthetic-2', at: at + 600, event: 'reserved', purchase_id: longReference, details: {} },
    { id: 'synthetic-1', at, event: 'activate', purchase_id: null, details: {} },
  ];
  let reads = 0;
  await page.route('**/v1/owner/overview', async route => { reads++; await route.fulfill({ json: data }); });
  await openWorkspace(page, scenario);
  await page.getByRole('button', { name: 'Timeline', exact: true }).click();
  const region = page.getByRole('region', { name: 'Your timeline', exact: true });
  const rows = region.getByRole('list', { name: 'Recorded events' }).getByRole('listitem');
  await expect(rows).toHaveCount(4);
  await expect(rows.getByRole('heading')).toHaveText(['approved', 'reserved', 'reserved', 'activate']);
  await expect(rows.locator('p')).toHaveText(['synthetic-cart-001', 'synthetic-cart-001', longReference, 'Financial plan']);
  for (let i = 0; i < data.events.length; i++) {
    await expect(rows.nth(i).locator('time')).toHaveAttribute('datetime', new Date(data.events[i]!.at * 1000).toISOString());
  }
  await expect(rows.first().locator('time')).toHaveText('10/23/2026, 10:12:00 AM');
  await expect(region.getByRole('button')).toHaveCount(1);
  await region.getByRole('button', { name: 'Refresh workspace' }).focus();
  await page.keyboard.press('Enter');
  await expect.poll(() => reads).toBe(2);
  await expect(page.getByRole('status')).toHaveCount(0);
  await expect(rows).toHaveCount(4);
  await checkTimeline(page, info);
  await expect(page).toHaveScreenshot('timeline-recorded-events.png', { fullPage: true });
});

import AxeBuilder from '@axe-core/playwright';
import { test, expect, openWorkspace, overview } from './fixtures';
import type { Page, TestInfo } from '@playwright/test';
import type { Scenario } from './fixtures';

async function checkAccessibility(page: Page, info: TestInfo) {
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  await info.attach('axe-results', { body: JSON.stringify(result, null, 2), contentType: 'application/json' });
  expect(result.violations.map(item => ({ rule: item.id, impact: item.impact,
    targets: item.nodes.map(node => node.target) }))).toEqual([]);
}

for (const screen of ['Plan', 'Purchases', 'Timeline']) {
  test(`${screen}: WCAG automated checks and reflow`, async ({ page, scenario }, info) => {
    await openWorkspace(page, scenario);
    await page.getByRole('navigation', { name: 'Workspace' }).getByRole('button', { name: screen === 'Plan' ? 'Budget and plan' : screen }).click();
    await expect.soft.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await checkAccessibility(page, info);
  });
}
for (const state of ['empty', 'loading', 'error', 'offline', 'locked', 'uncertain'] as Scenario[]) {
  test.describe(state, () => {
    test.use({ scenario: state });
    test('state has accessible content', async ({ page, scenario }, info) => {
      await openWorkspace(page, scenario);
      if (scenario === 'uncertain') {
        await page.getByRole('button', { name: 'Purchases' }).click();
        await expect(page.getByText(/Budget remains committed/)).toBeVisible();
        await expect(page.getByRole('button', { name: 'Refresh payment status' })).toBeVisible();
        await expect(page.getByRole('button', { name: 'Capture after manual fulfilment' })).toHaveCount(0);
      }
      await checkAccessibility(page, info);
    });
  });
}
test('keyboard skip link reaches main and session expiry locks without replay', async ({ page, scenario }) => {
  await page.clock.install({ time: new Date('2026-10-23T10:00:00Z') });
  await openWorkspace(page, scenario);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#main$/);
  await expect(page.locator('main')).toBeFocused();
  await page.clock.fastForward(1800_000);
  await expect(page.getByRole('alert')).toContainText('Session expired');
  await expect(page.getByLabel('Owner key', { exact: true })).toBeVisible();
});

test('large amounts and long request names remain readable without horizontal scrolling', async ({ page, scenario }) => {
  const data = overview('ready');
  data.plan!.cash_base_cents = 1_000_000_000_000;
  data.plan!.available_cents = 999_999_965_000;
  data.purchases[0]!.agent = 'A synthetic agent with an unusually long descriptive name';
  await page.route('**/v1/owner/overview', route => route.fulfill({ json: data }));
  await openWorkspace(page, scenario);
  await expect(page.locator('.amount')).toHaveText('$9,999,999,650.00');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

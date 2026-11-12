import AxeBuilder from '@axe-core/playwright';
import { test, expect, openWorkspace, overview } from './fixtures';

for (const longNames of [false, true]) test(`confirmation reveals the budget with ${longNames ? 'long names' : 'normal names'} and deliberate editing`, async ({ page, scenario }, info) => {
  const view = overview('ready');
  if (longNames) {
    view.plan!.spec.title = 'HouseholdBudget'.repeat(8);
    view.plan!.spec.bills[0]!.name = 'Utilities'.repeat(12);
    view.plan!.spec.goal!.title = 'Equipment'.repeat(12);
  }
  await page.route('**/v1/owner/overview', route => route.fulfill({ json: view }));
  const confirmations: unknown[] = [];
  await page.route('**/v1/plan/preview', async route => {
    const body = route.request().postDataJSON();
    await route.fulfill({ json: { spec: body.plan, mode: body.mode, summary: view.plan,
      preview_hash: 'synthetic-reviewed-budget', activation_blocked_by: null, releases_purchase_ids: [] } });
  });
  await page.route('**/v1/plan/confirm', async route => {
    confirmations.push(route.request().postDataJSON());
    await route.fulfill({ json: view.plan });
  });
  await openWorkspace(page, scenario);
  await page.getByRole('button', { name: 'Preview protections' }).click();
  await page.getByRole('button', { name: 'Confirm this plan' }).click();
  const heading = page.getByRole('heading', { level: 1 });
  await expect(heading).toBeFocused();
  await expect(heading).toBeInViewport({ ratio: 1 });
  await expect(page.getByRole('button', { name: 'Preview protections' })).toBeHidden();
  await expect(page.getByRole('button', { name: 'Confirm this plan' })).toHaveCount(0);
  const budget = page.getByRole('region', { name: 'Confirmed budget plan' });
  await expect(budget).toContainText(`${view.plan!.spec.bills[0]!.name}: $100.00, due 2026-11-02.`);
  await expect(budget).toContainText(`${view.plan!.spec.goal!.title}: target $600.00`);
  await expect(budget).toContainText('Expected income: $400.00 on 2026-11-05.');
  await expect(page.locator('.amount')).toHaveText('$250.00');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  expect(result.violations.map(item => item.id)).toEqual([]);
  // Axe probes focusable controls; restore the actual post-confirmation target
  // before capturing the owner's landing view.
  await heading.focus();
  await page.screenshot({ path: info.outputPath('confirmed-budget.png'), fullPage: true });
  await page.screenshot({ path: info.outputPath('confirmed-budget-viewport.png') });
  const edit = page.getByRole('button', { name: 'Edit plan' });
  await edit.focus(); await page.keyboard.press('Enter');
  await expect(page.getByLabel('Current cash (USD)', { exact: true })).toBeFocused();
  await expect(page.getByRole('button', { name: 'Preview protections' })).toBeVisible();
  await expect(page.getByLabel('Plan change', { exact: true })).toHaveValue('revise');
  expect(confirmations).toEqual([{ plan: view.plan!.spec, mode: 'revise', preview_hash: 'synthetic-reviewed-budget' }]);
});

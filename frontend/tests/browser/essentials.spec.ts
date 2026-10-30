import { test, expect, openWorkspace } from './fixtures';

test('essentials are visible while optional values survive keyboard disclosure changes', async ({ page, scenario }) => {
  await openWorkspace(page, scenario);
  await expect(page.getByLabel('Current cash (USD)', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Next payday', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Bill 1 name', { exact: true })).not.toBeVisible();
  await expect(page.getByLabel('Savings goal', { exact: true })).not.toBeVisible();
  const bills = page.locator('summary').filter({ hasText: 'Bills to protect' });
  await bills.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByLabel('Bill 1 name', { exact: true })).toHaveValue('Demo utilities');
  await expect(page.getByLabel('Bill 1 name', { exact: true })).toBeVisible();
  await bills.press('Enter');
  await expect(page.getByLabel('Bill 1 name', { exact: true })).not.toBeVisible();
  await bills.press('Enter');
  await expect(page.getByLabel('Bill 1 amount (USD)', { exact: true })).toHaveValue('100.00');
});

test.describe('new plan', () => {
  test.use({ scenario: 'empty' });
  test('required plan details are revealed rather than bypassed', async ({ page, scenario }) => {
    await openWorkspace(page, scenario);
    await page.getByLabel('Current cash (USD)', { exact: true }).fill('600');
    await page.getByLabel('Cash buffer (USD)', { exact: true }).fill('50');
    await page.getByLabel('Next payday', { exact: true }).fill('2026-11-05');
    await page.getByLabel('Expected income (USD)', { exact: true }).fill('400');
    await expect(page.getByLabel('Plan name', { exact: true })).not.toBeVisible();
    await page.getByRole('button', { name: 'Preview protections' }).click();
    await expect(page.getByLabel('Plan name', { exact: true })).toBeVisible();
    await expect(page.getByLabel('Plan name', { exact: true })).toBeFocused();
    await expect(page.getByRole('button', { name: 'Confirm this plan' })).toHaveCount(0);
  });
});

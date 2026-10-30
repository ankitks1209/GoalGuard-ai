import AxeBuilder from '@axe-core/playwright';
import { test, expect, openWorkspace, overview } from './fixtures';
import type { Page, TestInfo } from '@playwright/test';

async function checkReview(page: Page, info: TestInfo) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  await info.attach('purchase-axe-results', { body: JSON.stringify(result, null, 2), contentType: 'application/json' });
  expect(result.violations.map(item => item.id)).toEqual([]);
}

for (const state of ['empty', 'loading', 'error', 'offline'] as const) {
  test.describe(`purchase state ${state}`, () => {
    test.use({ scenario: state });
    test('shows known empty or unread status accurately', async ({ page, scenario }, info) => {
      await openWorkspace(page, scenario);
      await page.getByRole('button', { name: 'Purchases', exact: true }).click();
      await expect(page.getByRole('heading', { name: 'Purchase requests', exact: true })).toHaveCount(1);
      if (state === 'empty') {
        await expect(page.getByRole('heading', { name: 'No purchase requests yet' })).toBeVisible();
        await expect(page.getByText('0 requests', { exact: true })).toBeVisible();
      } else {
        await expect(page.getByRole('heading', { name: 'No purchase requests yet' })).toHaveCount(0);
        await expect(page.getByText('Request count unavailable', { exact: true })).toBeVisible();
        if (state === 'loading') await expect(page.getByRole('status')).toHaveText('Loading purchase requests…');
        else await expect(page.getByText('Purchase requests are unavailable. Refresh workspace to read current status.')).toBeVisible();
      }
      await checkReview(page, info);
      await expect(page).toHaveScreenshot(`purchases-${state}.png`, { fullPage: true });
    });
  });
}

test('keyboard consent belongs to one exact cart and changed terms require fresh consent', async ({ page, scenario }, info) => {
  const data = overview('ready');
  const first = data.purchases[0]!;
  first.agent = 'A synthetic shopping agent with a deliberately long descriptive name';
  first.cart.items[0]!.sku = 'synthetic-catalog-item-with-a-deliberately-long-unbroken-name';
  data.purchases.push({ ...first, id: 'second-cart', agent: 'Second agent', cart_hash: 'second-hash' });
  await page.route('**/v1/owner/overview', route => route.fulfill({ json: data }));
  await openWorkspace(page, scenario);
  await page.getByRole('button', { name: 'Purchases', exact: true }).click();
  const firstCart = page.getByRole('article', { name: 'Purchase synthetic-cart', exact: true });
  const secondCart = page.getByRole('article', { name: 'Purchase second-cart', exact: true });
  const consent = firstCart.getByRole('checkbox');
  await expect(firstCart.getByRole('button', { name: 'Approve exact cart' })).toBeDisabled();
  await consent.focus();
  await page.keyboard.press('Space');
  await expect(consent).toBeChecked();
  await page.keyboard.press('Tab');
  await expect(firstCart.getByRole('button', { name: 'Approve exact cart' })).toBeFocused();
  await expect(secondCart.getByRole('checkbox')).not.toBeChecked();
  await expect(secondCart.getByRole('button', { name: 'Approve exact cart' })).toBeDisabled();
  first.cart_hash = 'changed-exact-cart';
  first.amount_cents = 20000;
  first.cart.items[0]!.quantity = 2;
  await page.getByRole('button', { name: 'Refresh workspace' }).click();
  await expect(firstCart.getByRole('checkbox')).not.toBeChecked();
  await expect(firstCart.getByRole('button', { name: 'Approve exact cart' })).toBeDisabled();
  await expect(firstCart.getByRole('checkbox')).toHaveAccessibleName('I approve these exact items and the $200.00 total.');
  await checkReview(page, info);
});

test('restored payment states retain exact carts and only their existing controls', async ({ page, scenario }, info) => {
  const data = overview('ready');
  const cart = data.purchases[0]!;
  data.purchases = ['approved', 'authorized', 'reconcile_pending', 'captured', 'expired'].map(state => ({
    ...cart, id: `synthetic-${state}`, state, permit: 'synthetic-existing-permit',
    order_id: state === 'approved' ? 'synthetic-existing-order' : null,
    operation_id: state === 'reconcile_pending' ? 'synthetic-existing-operation' : null,
  }));
  await page.route('**/v1/owner/overview', route => route.fulfill({ json: data }));
  await openWorkspace(page, scenario);
  await page.getByRole('button', { name: 'Purchases', exact: true }).click();
  const approved = page.getByRole('article', { name: 'Purchase synthetic-approved', exact: true });
  await expect(approved.getByRole('button', { name: 'Create sandbox checkout' })).toBeEnabled();
  await expect(approved.getByRole('button', { name: 'Verify buyer approval and authorize' })).toBeEnabled();
  const authorized = page.getByRole('article', { name: 'Purchase synthetic-authorized', exact: true });
  await expect(authorized.getByRole('button', { name: 'Capture after manual fulfilment' })).toBeDisabled();
  await expect(authorized.getByRole('button', { name: 'Void authorization' })).toBeEnabled();
  const pending = page.getByRole('article', { name: 'Purchase synthetic-reconcile_pending', exact: true });
  await expect(pending.getByText(/Budget remains committed/)).toBeVisible();
  await expect(pending.getByRole('button')).toHaveCount(1);
  await expect(pending.getByRole('button', { name: 'Refresh payment status' })).toBeEnabled();
  await expect(page.getByRole('article', { name: 'Purchase synthetic-captured', exact: true }).getByText(/Captured spending stays deducted/)).toBeVisible();
  const expired = page.getByRole('article', { name: 'Purchase synthetic-expired', exact: true });
  await expect(expired.getByText(/This request is closed/)).toBeVisible();
  await expect(expired.getByRole('button')).toHaveCount(0);
  await expect(page.getByRole('table', { name: 'Exact cart · USD' })).toHaveCount(5);
  await checkReview(page, info);
  await expect(page).toHaveScreenshot('purchases-payment-states.png', { fullPage: true });
});

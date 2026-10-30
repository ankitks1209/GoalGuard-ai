import AxeBuilder from '@axe-core/playwright';
import { test, expect, openWorkspace, overview } from './fixtures';
import type { Page, TestInfo } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(crypto, 'randomUUID', { value: () => '00000000-0000-4000-8000-000000000001' });
  });
});

async function inspect(page: Page, info: TestInfo, name: string) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze();
  expect(result.violations.map(item => ({ rule: item.id, targets: item.nodes.map(node => node.target) }))).toEqual([]);
  await info.attach(`${name}-axe`, { body: JSON.stringify(result), contentType: 'application/json' });
  await page.screenshot({ path: info.outputPath(`${name}.png`), fullPage: true });
  await page.locator(name.startsWith('financial') ? '.cash-events' : '.ai-draft').screenshot({ path: info.outputPath(`${name}-controls.png`) });
  if (name === 'ai-sample-review') await page.locator('.panel.review').screenshot({ path: info.outputPath(`${name}-confirmation.png`) });
  await expect(page).toHaveScreenshot(`${name}.png`, { fullPage: true });
}

test.describe('sample-only AI drafting', () => {
  test.use({ scenario: 'empty' });
  test('consent precedes the fixed sample request and the draft still needs separate confirmation', async ({ page, scenario }, info) => {
    const requests: unknown[] = [];
    const plan = overview('ready').plan!;
    await page.route('**/v1/plan/draft', async route => {
      requests.push(route.request().postDataJSON());
      await route.fulfill({ json: { status: 'draft_ready', preview: { spec: plan.spec, mode: 'activate',
        summary: plan, preview_hash: 'sample-reviewed-preview', activation_blocked_by: null, releases_purchase_ids: [] } } });
    });
    await openWorkspace(page, scenario);
    const disclosure = page.locator('.ai-draft summary');
    await disclosure.focus(); await page.keyboard.press('Enter');
    const sample = page.getByLabel('Sample text sent to Gemini');
    await expect(sample).toHaveAttribute('readonly', '');
    const create = page.getByRole('button', { name: 'Create sample AI draft' });
    await expect(create).toBeDisabled();
    expect(requests).toHaveLength(0);
    await page.getByLabel('I agree to send this sample to Google Gemini for drafting.').check();
    await create.click();
    await expect(page.getByRole('heading', { name: 'Review your protections' })).toBeVisible();
    expect(requests).toEqual([{ request: await sample.inputValue(), timezone: 'UTC', currency: 'USD', allow_model_processing: true }]);
    await expect(page.getByRole('button', { name: 'Confirm this plan' })).toBeEnabled();
    await inspect(page, info, 'ai-sample-review');
    await page.getByLabel('Cash buffer (USD)', { exact: true }).fill('60');
    await expect(page.getByRole('button', { name: 'Confirm this plan' })).toHaveCount(0);
  });

  test('loading and provider failure preserve manual fallback without retrying', async ({ page, scenario }, info) => {
    let release = () => {};
    const held = new Promise<void>(resolve => { release = resolve; });
    let calls = 0;
    await page.route('**/v1/plan/draft', async route => {
      calls++; await held;
      await route.fulfill({ status: 503, json: { reason: 'model_unavailable', message: 'Sample provider is unavailable.' } });
    });
    try {
      await openWorkspace(page, scenario);
      await page.locator('.ai-draft summary').click();
      await page.getByLabel('I agree to send this sample to Google Gemini for drafting.').check();
      await page.getByRole('button', { name: 'Create sample AI draft' }).click();
      await expect(page.getByRole('status')).toContainText('Creating a sample draft');
      await expect(page.getByRole('button', { name: 'Preview protections' })).toBeDisabled();
      await inspect(page, info, 'ai-sample-loading');
      release();
      await expect(page.getByRole('alert')).toContainText('Manual entry below remains available');
      await expect(page.getByRole('button', { name: 'Preview protections' })).toBeEnabled();
      await expect(page.getByRole('button', { name: 'Confirm this plan' })).toHaveCount(0);
      await inspect(page, info, 'ai-sample-error');
      expect(calls).toBe(1);
    } finally { release(); }
  });
});

test('owner reviews a paired bill record and sees refreshed accounting and Timeline', async ({ page, scenario }, info) => {
  const requests: Record<string, unknown>[] = [];
  let view = overview('ready');
  await page.route('**/v1/owner/overview', route => route.fulfill({ json: view }));
  await page.route('**/v1/plan/cash-events', async route => {
    const body = route.request().postDataJSON(); requests.push(body);
    view = { ...view, plan: { ...view.plan!, cash_base_cents: 56000, protected_cents: 21000,
      protected_bills_cents: 6000, encumbered_cents: 0, available_cents: 35000 },
      purchases: view.purchases.map(purchase => ({ ...purchase, state: 'released' })),
      events: [{ id: 'synthetic-cash-record', at: 1792749600, event: 'cash_recorded', purchase_id: null, details: body }] };
    await route.fulfill({ json: { recorded: true, event_id: body.event_id, summary: view.plan } });
  });
  await openWorkspace(page, scenario);
  const disclosure = page.locator('.cash-events summary');
  await disclosure.focus(); await page.keyboard.press('Enter');
  await page.getByLabel('Activity', { exact: true }).selectOption('bill_payment');
  await page.getByLabel('Amount (USD)', { exact: true }).fill('40');
  await page.getByLabel('Linked bill', { exact: true }).selectOption('demo-bill');
  await page.getByRole('button', { name: 'Review update' }).click();
  await expect(page.getByRole('button', { name: 'Record this update' })).toBeDisabled();
  expect(requests).toHaveLength(0);
  await inspect(page, info, 'financial-record-review');
  await page.getByLabel('I confirm this already happened outside GoalGuard.').check();
  await page.getByRole('button', { name: 'Record this update' }).click();
  await expect(page.getByRole('status')).toContainText('Financial update recorded');
  expect(requests).toEqual([{ event_id: expect.any(String), kind: 'bill_payment', amount_cents: 4000, reference_id: 'demo-bill' }]);
  await expect(page.locator('.amount')).toHaveText('$350.00');
  await page.getByRole('button', { name: 'Timeline', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'cash recorded', exact: true })).toBeVisible();
  await expect(page.getByText('bill payment: $40.00.')).toBeVisible();
  await expect(page.getByText('Record ID: 00000000-0000-4000-8000-000000000001')).toBeVisible();
});

test('a lost record response requires a read and never replays a mutation automatically', async ({ page, scenario }, info) => {
  let payload: Record<string, unknown> | null = null;
  let calls = 0;
  await page.route('**/v1/plan/cash-events', async route => {
    calls++; payload = route.request().postDataJSON(); await route.abort('internetdisconnected');
  });
  await page.route('**/v1/plan/audit', route => route.fulfill({ json: { events: [{ event: 'cash_recorded', details: payload }] } }));
  await openWorkspace(page, scenario);
  await page.locator('.cash-events summary').click();
  await page.getByLabel('Activity', { exact: true }).selectOption('savings_deposit');
  await page.getByLabel('Amount (USD)', { exact: true }).fill('25.50');
  await page.getByLabel('Linked savings goal', { exact: true }).selectOption('demo-goal');
  await page.getByRole('button', { name: 'Review update' }).click();
  await page.getByLabel('I confirm this already happened outside GoalGuard.').check();
  await page.getByRole('button', { name: 'Record this update' }).click();
  await expect(page.getByRole('button', { name: 'Check recorded status' })).toBeVisible();
  await expect(page.getByLabel('Amount (USD)', { exact: true })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Retry this same record' })).toHaveCount(0);
  await inspect(page, info, 'financial-record-uncertain');
  await page.getByRole('button', { name: 'Check recorded status' }).click();
  await expect(page.getByRole('status')).toContainText('already recorded');
  expect(calls).toBe(1);
});

import { test as base, expect } from '@playwright/test';
import type { Overview, Purchase } from '../../src/types';

export type Scenario = 'ready' | 'empty' | 'loading' | 'error' | 'offline' | 'locked' | 'uncertain';
export const instant = new Date('2026-10-23T10:00:00Z');
const purchase: Purchase = {
  id: 'synthetic-cart', agent: 'Demo agent', state: 'reserved', cart_hash: 'synthetic-exact-cart',
  amount_cents: 10000, expires_at: instant.getTime() / 1000 + 900,
  permit: null, operation_id: null, order_id: null,
  cart: { merchant: 'Synthetic catalog', currency: 'USD', shipping_cents: 0, tax_cents: 0,
    items: [{ sku: 'mic-standard', quantity: 1, unit_cents: 10000 }] },
};
export function overview(scenario: Scenario): Overview {
  if (scenario === 'empty') return { plan: null, draft: null, purchases: [], events: [] };
  return {
    draft: null,
    plan: {
      title: 'Synthetic household', status: 'ready', can_propose: true,
      spec: { title: 'Synthetic household', timezone: 'UTC', currency: 'USD',
        opening_cash_cents: 60000, buffer_cents: 5000,
        next_income: { id: 'demo-income', due_date: '2026-11-05', amount_cents: 40000 },
        bills: [{ id: 'demo-bill', name: 'Demo utilities', amount_cents: 10000, due_date: '2026-11-02' }],
        goal: { id: 'demo-goal', title: 'Demo equipment', target_cents: 60000,
          current_saved_cents: 30000, target_date: '2026-12-31', contribution_cents: 10000 } },
      cash_base_cents: 60000, protected_cents: 25000, protected_bills_cents: 10000,
      buffer_cents: 5000, remaining_goal_contribution_cents: 10000,
      encumbered_cents: 10000, spent_cents: 0, available_cents: 25000, projected_surplus_cents: 65000,
    },
    purchases: [{ ...purchase, cart: { ...purchase.cart, items: purchase.cart.items.map(item => ({ ...item })) }, ...(scenario === 'uncertain'
      ? { state: 'reconcile_pending', operation_id: 'synthetic-original-operation' } : {}) }],
    events: [{ id: 'synthetic-event', at: instant.getTime() / 1000,
      event: 'reserved', purchase_id: purchase.id, details: {} }],
  };
}

export const test = base.extend<{ scenario: Scenario; synthetic: void }>({
  scenario: ['ready', { option: true }],
  synthetic: [async ({ context, page, scenario, baseURL }, use) => {
    const unexpected: string[] = [];
    let release = () => {};
    const held = new Promise<void>(resolve => { release = resolve; });
    // Freeze Date, not browser timers: axe needs requestAnimationFrame/timeouts.
    await page.clock.setFixedTime(instant);
    await context.route('**/*', async route => {
      const request = route.request();
      const url = new URL(request.url());
      if (url.origin !== baseURL) {
        unexpected.push(`${request.method()} ${url.origin}${url.pathname}`);
        await route.abort('blockedbyclient'); return;
      }
      if (!url.pathname.startsWith('/v1/')) { await route.continue(); return; }
      if (request.method() !== 'GET') {
        unexpected.push(`${request.method()} ${url.pathname}`);
        await route.abort('blockedbyclient'); return;
      }
      if (url.pathname === '/v1/owner/session') {
        await route.fulfill({ status: scenario === 'locked' ? 401 : 200,
          json: scenario === 'locked' ? { reason: 'unauthorized' }
            : { csrf_token: 'synthetic-session-only', expires_in_seconds: 1800 } });
      } else if (url.pathname === '/v1/owner/overview') {
        if (scenario === 'loading') await held;
        if (scenario === 'offline') { await route.abort('internetdisconnected'); return; }
        await route.fulfill({ status: scenario === 'error' ? 503 : 200,
          json: scenario === 'error'
            ? { reason: 'synthetic_unavailable', message: 'Synthetic server unavailable. Refresh status.' }
            : overview(scenario) });
      } else {
        unexpected.push(`${request.method()} ${url.pathname}`);
        await route.abort('blockedbyclient');
      }
    });
    try { await use(); }
    finally {
      release();
      await context.unrouteAll({ behavior: 'wait' });
      expect(unexpected, 'Unexpected API mutation or external destination').toEqual([]);
    }
  }, { auto: true }],
});
export { expect };

export async function openWorkspace(page: import('@playwright/test').Page, scenario: Scenario) {
  await page.goto('/');
  if (scenario === 'locked') await expect(page.getByLabel('Owner key', { exact: true })).toBeVisible();
  else if (scenario === 'loading') await expect(page.getByText('Loading your workspace…')).toBeVisible();
  else if (scenario === 'error') await expect(page.getByRole('alert')).toContainText('Synthetic server unavailable');
  else if (scenario === 'offline') await expect(page.getByRole('alert')).toContainText('Could not connect');
  else if (scenario === 'empty') await expect(page.getByRole('heading', { name: 'No plan confirmed yet' })).toBeVisible();
  else await expect(page.getByRole('heading', { name: 'Your financial plan' })).toBeVisible();
  await page.evaluate(() => document.fonts.ready.then(() => undefined));
}

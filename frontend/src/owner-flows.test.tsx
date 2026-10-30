import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { Setup } from './Setup';
import type { Overview, Purchase } from './types';

const summary = { status: 'ready', can_propose: true, cash_base_cents: 60000, protected_cents: 25000,
  protected_bills_cents: 10000, buffer_cents: 5000, remaining_goal_contribution_cents: 10000,
  encumbered_cents: 0, spent_cents: 0, available_cents: 35000, projected_surplus_cents: 75000 };
const purchase: Purchase = { id: 'fixture-purchase', agent: 'agent-a', state: 'reserved', cart_hash: 'exact-cart-hash',
  amount_cents: 22000, expires_at: Date.now() / 1000 + 900, permit: null, operation_id: null, order_id: null,
  cart: { merchant: 'demo-merchant', currency: 'USD', items: [{ sku: 'mic-standard', quantity: 1, unit_cents: 22000 }], shipping_cents: 0, tax_cents: 0 } };
let overview: Overview;
const fetcher = vi.fn();
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });
beforeEach(() => {
  overview = { plan: null, draft: null, purchases: [], events: [] };
  vi.stubGlobal('fetch', fetcher);
  fetcher.mockReset().mockImplementation(async (path: string) => path === '/v1/owner/session'
    ? json({ csrf_token: 'fixture-csrf', expires_in_seconds: 1800 }) : json(overview));
});
afterEach(() => vi.unstubAllGlobals());
function fill(label: string, value: string) { fireEvent.change(screen.getByLabelText(label), { target: { value } }); }
async function form() {
  await screen.findByLabelText('Plan name');
  fill('Plan name', 'Our plan'); fill('Timezone', 'UTC'); fill('Current cash (USD)', '600'); fill('Cash buffer (USD)', '50');
  fill('Next payday', '2026-11-05'); fill('Expected income (USD)', '400');
}

it('previews integer cents and requires a separate confirmation of the exact returned plan', async () => {
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === '/v1/owner/session') return json({ csrf_token: 'fixture-csrf', expires_in_seconds: 1800 });
    if (path === '/v1/plan/preview') {
      const body = JSON.parse(String(init?.body));
      return json({ spec: body.plan, mode: 'activate', summary, preview_hash: 'reviewed-preview', activation_blocked_by: null, releases_purchase_ids: [] });
    }
    if (path === '/v1/plan/confirm') return json(summary);
    return json(overview);
  });
  render(<Setup />); await form();
  fireEvent.click(screen.getByRole('button', { name: 'Preview protections' }));
  await screen.findByRole('heading', { name: 'Review your protections' });
  const preview = fetcher.mock.calls.find(([path]) => path === '/v1/plan/preview');
  expect(JSON.parse(String(preview?.[1].body)).plan.opening_cash_cents).toBe(60000);
  expect(fetcher.mock.calls.some(([path]) => path === '/v1/plan/confirm')).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: 'Confirm this plan' }));
  await waitFor(() => expect(fetcher.mock.calls.some(([path]) => path === '/v1/plan/confirm')).toBe(true));
  const confirmation = fetcher.mock.calls.find(([path]) => path === '/v1/plan/confirm');
  expect(JSON.parse(String(confirmation?.[1].body)).preview_hash).toBe('reviewed-preview');
});

it('invalidates previews when input changes and rejects fractional cents before the API', async () => {
  render(<Setup />); await form();
  fill('Current cash (USD)', '12.001');
  fireEvent.click(screen.getByRole('button', { name: 'Preview protections' }));
  await screen.findByText(/at most two decimal places/);
  expect(fetcher.mock.calls.some(([path]) => path === '/v1/plan/preview')).toBe(false);
});

it('keeps optional sections collapsed and preserves their terms in the exact preview', async () => {
  const spec = { title: 'Existing plan', timezone: 'UTC', currency: 'USD' as const, opening_cash_cents: 60000, buffer_cents: 5000,
    next_income: { id: 'pay', due_date: '2026-11-05', amount_cents: 40000 },
    bills: [{ id: 'bill', name: 'Utilities', amount_cents: 10000, due_date: '2026-11-02' }],
    goal: { id: 'goal', title: 'Equipment', target_cents: 60000, current_saved_cents: 30000,
      target_date: '2026-12-31', contribution_cents: 10000 } };
  overview.plan = { ...summary, spec };
  const responses = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/preview'
    ? json({ spec: JSON.parse(String(init?.body)).plan, mode: 'revise', summary, preview_hash: 'retained', activation_blocked_by: null, releases_purchase_ids: [] })
    : responses(path, init));
  render(<Setup />);
  await screen.findByDisplayValue('Existing plan');
  for (const label of ['Bill 1 name', 'Savings goal', 'Plan name']) {
    expect(screen.getByLabelText(label).closest('details')?.open).toBe(false);
  }
  fireEvent.click(screen.getByRole('button', { name: 'Preview protections' }));
  await screen.findByRole('heading', { name: 'Review your protections' });
  const request = fetcher.mock.calls.find(([path]) => path === '/v1/plan/preview');
  expect(JSON.parse(String(request?.[1].body)).plan).toEqual(spec);
  expect(fetcher.mock.calls.some(([path]) => path === '/v1/plan/confirm')).toBe(false);
});

it('renders exact-cart review and sends only the displayed hash after explicit consent', async () => {
  overview.purchases = [purchase];
  render(<Setup />); await screen.findByRole('button', { name: 'Lock workspace' });
  fireEvent.click(screen.getByRole('button', { name: /Purchases/ }));
  await screen.findByText('mic-standard');
  const approve = screen.getByRole('button', { name: 'Approve exact cart' });
  expect(approve).toHaveProperty('disabled', true);
  fireEvent.click(screen.getByLabelText(/I approve these exact items/));
  fireEvent.click(approve);
  await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/v1/purchases/fixture-purchase/approve', expect.objectContaining({
    body: JSON.stringify({ cart_hash: 'exact-cart-hash' }), headers: expect.objectContaining({ 'X-CSRF-Token': 'fixture-csrf' }),
  })));
});

it('opens an exact-cart review from the budget summary without granting consent or executing payment', async () => {
  overview.purchases = [purchase];
  render(<Setup />);
  const review = await screen.findByRole('button', { name: 'Review cart from agent-a' });
  expect(screen.queryByRole('button', { name: 'Approve exact cart' })).toBeNull();
  fireEvent.click(review);
  expect(await screen.findByRole('button', { name: 'Approve exact cart' })).toHaveProperty('disabled', true);
  expect(screen.getByLabelText(/I approve these exact items/)).toHaveProperty('checked', false);
  expect(fetcher.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false);
});

it('keeps uncertain payments committed and offers only an explicit status refresh with the original operation', async () => {
  overview.purchases = [{ ...purchase, state: 'reconcile_pending', operation_id: 'original-operation' }];
  render(<Setup />); await screen.findByRole('button', { name: 'Lock workspace' });
  fireEvent.click(screen.getByRole('button', { name: /Purchases/ }));
  await screen.findByText(/Budget remains committed/);
  expect(screen.queryByRole('button', { name: 'Capture after manual fulfilment' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Refresh payment status' }));
  await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/v1/purchases/fixture-purchase/refresh', expect.objectContaining({
    body: JSON.stringify({ operation_id: 'original-operation' }),
  })));
  expect(fetcher.mock.calls.some(([path]) => String(path).endsWith('/capture'))).toBe(false);
});

it('renders an empty timeline, then recorded events without executing payments', async () => {
  overview.events = [{ id: 'evt-1', at: 1792670489, event: 'reserved', purchase_id: 'fixture-purchase', details: {} }];
  render(<Setup />); await screen.findByRole('button', { name: 'Lock workspace' });
  fireEvent.click(screen.getByRole('button', { name: /Timeline/ }));
  expect(await screen.findByText('reserved')).toBeTruthy();
  expect(screen.getByText('fixture-purchase')).toBeTruthy();
});

it('lets owners enter bills and a savings goal, then invalidates the reviewed preview on an edit', async () => {
  const responses = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === '/v1/plan/preview') {
      const body = JSON.parse(String(init?.body));
      return json({ spec: body.plan, mode: 'activate', summary: { ...summary, goal: { suggested_contribution_cents: 10000 } }, preview_hash: 'exact', activation_blocked_by: null, releases_purchase_ids: ['old-reservation'] });
    }
    return responses(path, init);
  });
  render(<Setup />); await form();
  fireEvent.click(screen.getByText('Bills to protect', { exact: true }));
  fireEvent.click(screen.getByRole('button', { name: '+ Add bill' }));
  fill('Bill 1 name', 'Utilities'); fill('Bill 1 amount (USD)', '100'); fill('Bill 1 due date', '2026-11-02');
  fireEvent.click(screen.getByLabelText('Include a savings goal'));
  fill('Savings goal', 'Equipment'); fill('Savings target (USD)', '600'); fill('Already saved (USD)', '300'); fill('Goal deadline', '2026-12-31'); fill('Monthly contribution (USD)', '100');
  fireEvent.click(screen.getByRole('button', { name: 'Preview protections' }));
  await screen.findByRole('heading', { name: 'Review your protections' });
  expect(screen.getByText(/releases 1 pre-payment reservation/)).toBeTruthy();
  expect(screen.getByText('old-reservation')).toBeTruthy();
  expect(screen.getByText(/Suggested monthly contribution/)).toBeTruthy();
  fill('Plan name', 'Changed plan');
  expect(screen.queryByRole('button', { name: 'Confirm this plan' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Remove bill 1' }));
  expect(screen.queryByLabelText('Bill 1 name')).toBeNull();
});

it('handles an unknown payday and a blocked preview without offering confirmation', async () => {
  const responses = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/preview'
    ? json({ spec: JSON.parse(String(init?.body)).plan, mode: 'activate', summary: { ...summary, status: 'waiting_for_income' }, preview_hash: 'blocked', activation_blocked_by: 'income_date_required', releases_purchase_ids: [] })
    : responses(path, init));
  render(<Setup />); await form();
  fireEvent.click(screen.getByLabelText('Next payday is not known yet'));
  fireEvent.click(screen.getByRole('button', { name: 'Preview protections' }));
  await screen.findByText(/Cannot confirm yet/);
  expect(screen.getByRole('button', { name: 'Confirm this plan' })).toHaveProperty('disabled', true);
  const request = fetcher.mock.calls.find(([path]) => path === '/v1/plan/preview');
  expect(JSON.parse(String(request?.[1].body)).plan.next_income).toBeNull();
});

it('restores a saved plan and rejects a stale confirmation without automatically replaying it', async () => {
  const spec = { title: 'Existing plan', timezone: 'UTC', currency: 'USD' as const, opening_cash_cents: 60000, buffer_cents: 5000,
    next_income: { id: 'pay', due_date: '2026-11-05', amount_cents: 40000 }, bills: [{ id: 'bill', name: 'Utilities', amount_cents: 10000, due_date: '2026-11-02' }],
    goal: { id: 'goal', title: 'Equipment', target_cents: 60000, current_saved_cents: 30000, target_date: '2026-12-31', contribution_cents: 10000 } };
  overview.plan = { ...summary, spec };
  const responses = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === '/v1/plan/preview') return json({ spec, mode: 'rollover', summary, preview_hash: 'stale', activation_blocked_by: null, releases_purchase_ids: [] });
    if (path === '/v1/plan/confirm') return json({ reason: 'stale_plan_preview', message: 'The plan changed. Review a fresh preview.' }, 409);
    return responses(path, init);
  });
  render(<Setup />);
  await screen.findByDisplayValue('Existing plan');
  expect(screen.getByLabelText('Bill 1 name')).toHaveProperty('value', 'Utilities');
  fireEvent.change(screen.getByLabelText('Plan change'), { target: { value: 'rollover' } });
  fireEvent.click(screen.getByRole('button', { name: 'Preview protections' }));
  await screen.findByRole('button', { name: 'Confirm this plan' });
  fireEvent.click(screen.getByRole('button', { name: 'Confirm this plan' }));
  await screen.findByText(/The plan changed/);
  expect(screen.queryByRole('button', { name: 'Confirm this plan' })).toBeNull();
  expect(fetcher.mock.calls.filter(([path]) => path === '/v1/plan/confirm')).toHaveLength(1);
});

it('shows empty purchase and timeline states and lets owners refresh without a mutation', async () => {
  render(<Setup />); await screen.findByRole('button', { name: 'Lock workspace' });
  fireEvent.click(screen.getByRole('button', { name: /Purchases/ }));
  expect(screen.getByRole('heading', { name: 'No purchase requests yet' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: /Timeline/ }));
  expect(screen.getByRole('heading', { name: 'A fresh start' })).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Refresh workspace' }));
  expect(fetcher.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false);
});

it('requires fulfilled-demo confirmation before capture and restores owner permits without minting new consent', async () => {
  overview.purchases = [{ ...purchase, state: 'authorized', permit: 'existing-consent-permit' }];
  render(<Setup />); await screen.findByRole('button', { name: 'Lock workspace' });
  fireEvent.click(screen.getByRole('button', { name: /Purchases/ }));
  const capture = screen.getByRole('button', { name: 'Capture after manual fulfilment' });
  expect(capture).toHaveProperty('disabled', true);
  fireEvent.click(screen.getByLabelText('I confirm manual demo fulfilment is complete.'));
  fireEvent.click(capture);
  await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/v1/purchases/fixture-purchase/capture', expect.objectContaining({ body: JSON.stringify({ permit: 'existing-consent-permit' }) })));
  expect(fetcher.mock.calls.some(([path]) => String(path).endsWith('/approve'))).toBe(false);
});

it('shows provider failure without retrying a payment and rejects unexpected checkout URLs', async () => {
  overview.purchases = [{ ...purchase, state: 'approved', permit: 'permit', order_id: 'order' }];
  const responses = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path.endsWith('/checkout')
    ? json({ approval_url: 'https://attacker.invalid/' }) : path.endsWith('/authorize')
      ? json({ reason: 'payment_unavailable', message: 'Provider unavailable.' }, 503) : responses(path, init));
  render(<Setup />); await screen.findByRole('button', { name: 'Lock workspace' });
  fireEvent.click(screen.getByRole('button', { name: /Purchases/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Create sandbox checkout' }));
  await screen.findByText(/unexpected checkout destination/);
  expect(screen.queryByRole('link', { name: /Continue to PayPal/ })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Verify buyer approval and authorize' }));
  await screen.findByText(/Provider unavailable/);
  expect(fetcher.mock.calls.filter(([path]) => path.endsWith('/authorize'))).toHaveLength(1);
});

it('offers a verified sandbox link, release, void and closed status without automatic navigation', async () => {
  overview.purchases = [
    { ...purchase, state: 'approved', permit: 'permit' },
    { ...purchase, id: 'authorized', state: 'authorized', permit: 'permit' },
    { ...purchase, id: 'captured', state: 'captured' },
    { ...purchase, id: 'released', state: 'released' },
  ];
  const responses = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path.endsWith('/checkout')
    ? json({ approval_url: 'https://www.sandbox.paypal.com/checkoutnow?token=fixture' }) : responses(path, init));
  render(<Setup />); await screen.findByRole('button', { name: 'Lock workspace' });
  fireEvent.click(screen.getByRole('button', { name: /Purchases/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Create sandbox checkout' }));
  const link = await screen.findByRole('link', { name: /Continue to PayPal sandbox/ });
  expect(link.getAttribute('href')).toMatch(/^https:\/\/www.sandbox.paypal.com\//);
  expect(screen.getByText(/Captured spending stays deducted/)).toBeTruthy();
  expect(screen.getByText(/request is closed/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Void authorization' }));
  await waitFor(() => expect(fetcher.mock.calls.some(([path]) => path.endsWith('/void'))).toBe(true));
  fireEvent.click(screen.getByRole('button', { name: 'Release reservation' }));
  await waitFor(() => expect(fetcher.mock.calls.some(([path]) => path.endsWith('/release'))).toBe(true));
});

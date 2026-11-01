import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { Setup } from './Setup';
import type { Overview, PlanSpec } from './types';

const spec: PlanSpec = { title: 'Synthetic plan', timezone: 'UTC', currency: 'USD', opening_cash_cents: 60000,
  buffer_cents: 5000, next_income: { id: 'pay', due_date: '2026-11-05', amount_cents: 40000 },
  bills: [{ id: 'bill', name: 'Utilities', amount_cents: 10000, due_date: '2026-11-02' }],
  goal: { id: 'goal', title: 'Equipment', target_cents: 60000, current_saved_cents: 30000,
    target_date: '2026-12-31', contribution_cents: 10000 } };
const summary = { spec, status: 'ready', can_propose: true, cash_base_cents: 60000, protected_cents: 25000,
  protected_bills_cents: 10000, buffer_cents: 5000, remaining_goal_contribution_cents: 10000,
  encumbered_cents: 0, spent_cents: 0, available_cents: 35000, projected_surplus_cents: 75000 };
const preview = { spec, mode: 'activate', summary, preview_hash: 'sample-preview', activation_blocked_by: null, releases_purchase_ids: [] };
let view: Overview;
const fetcher = vi.fn();
const reply = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });
const fill = (label: string, value: string) => fireEvent.change(screen.getByLabelText(label), { target: { value } });
const posts = (path: string) => fetcher.mock.calls.filter(([url, init]) => url === path && init?.method === 'POST');
beforeEach(() => {
  view = { plan: null, draft: null, purchases: [], events: [] };
  vi.stubGlobal('fetch', fetcher);
  fetcher.mockReset().mockImplementation(async (path: string) => path === '/v1/owner/session'
    ? reply({ csrf_token: 'fixture-session', expires_in_seconds: 1800 }) : reply(view));
});
afterEach(() => vi.unstubAllGlobals());

async function openDraft() {
  render(<Setup />);
  await screen.findByRole('heading', { name: 'No plan confirmed yet' });
  fireEvent.click(await screen.findByText('Try AI drafting with sample data', { exact: true }));
}
async function openUpdate(kind = 'bill_payment', reference = 'bill', amount = '40') {
  view.plan = { ...summary, spec: structuredClone(spec) };
  render(<Setup />);
  fireEvent.click(await screen.findByText('Record a financial update', { exact: true }));
  fill('Activity', kind); fill('Amount (USD)', amount);
  if (reference) fireEvent.change(screen.getByLabelText(/Linked /), { target: { value: reference } });
}

it('sends only the displayed fixed sample after consent and never activates an AI draft', async () => {
  const normal = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/draft'
    ? reply({ status: 'draft_ready', preview, plan: spec, computed_fields: ['goal.contribution_cents'] }) : normal(path, init));
  await openDraft();
  fill('Plan name', 'Private manual label that must not be sent');
  const create = screen.getByRole('button', { name: 'Create sample AI draft' });
  expect(create).toHaveProperty('disabled', true);
  const sample = screen.getByLabelText('Sample text sent to Gemini') as HTMLTextAreaElement;
  expect(sample.readOnly).toBe(true);
  fireEvent.click(screen.getByLabelText('I agree to send this sample to Google Gemini for drafting.'));
  fireEvent.click(create);
  await screen.findByRole('heading', { name: 'Review your protections' });
  const body = JSON.parse(String(posts('/v1/plan/draft')[0]?.[1]?.body));
  expect(body).toEqual({ request: sample.value, timezone: 'UTC', currency: 'USD', allow_model_processing: true });
  expect(JSON.stringify(body)).not.toContain('Private manual label');
  expect(posts('/v1/plan/confirm')).toHaveLength(0);
  expect(screen.getByLabelText('Plan name')).toHaveProperty('value', spec.title);
  fill('Cash buffer (USD)', '60');
  expect(screen.queryByRole('button', { name: 'Confirm this plan' })).toBeNull();
});

it('keeps manual entry available after clarification or provider failure, without automatic retries', async () => {
  const normal = fetcher.getMockImplementation()!;
  let call = 0;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/draft'
    ? ++call === 1 ? reply({ status: 'needs_clarification', questions: ['Which bills need protection?'] })
      : reply({ reason: 'draft_unavailable', message: 'Drafting is unavailable. Use manual entry.' }, 409) : normal(path, init));
  await openDraft();
  fireEvent.click(screen.getByLabelText('I agree to send this sample to Google Gemini for drafting.'));
  fireEvent.click(screen.getByRole('button', { name: 'Create sample AI draft' }));
  await screen.findByText('Which bills need protection?');
  expect(posts('/v1/plan/draft')).toHaveLength(1);
  expect(screen.queryByRole('button', { name: 'Confirm this plan' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Create sample AI draft' }));
  await screen.findByText(/Drafting is unavailable/);
  expect(posts('/v1/plan/draft')).toHaveLength(2);
  expect(screen.getByRole('button', { name: 'Preview protections' })).toHaveProperty('disabled', false);
});

it('reviews a paired bill record and sends integer cents only after separate confirmation', async () => {
  const normal = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/cash-events'
    ? reply({ recorded: true, event_id: JSON.parse(String(init?.body)).event_id, summary }) : normal(path, init));
  await openUpdate();
  fireEvent.click(screen.getByRole('button', { name: 'Review update' }));
  await screen.findByRole('heading', { name: 'Review this financial record' });
  expect(posts('/v1/plan/cash-events')).toHaveLength(0);
  const confirm = screen.getByRole('button', { name: 'Record this update' });
  expect(confirm).toHaveProperty('disabled', true);
  fireEvent.click(screen.getByLabelText('I confirm this already happened outside GoalGuard.'));
  fireEvent.click(confirm); fireEvent.click(confirm);
  await screen.findByText(/Financial update recorded/);
  expect(posts('/v1/plan/cash-events')).toHaveLength(1);
  expect(JSON.parse(String(posts('/v1/plan/cash-events')[0]?.[1]?.body))).toEqual({
    event_id: expect.any(String), kind: 'bill_payment', amount_cents: 4000, reference_id: 'bill',
  });
  expect(fetcher.mock.calls.some(([path]) => /\/(capture|authorize|checkout)$/.test(path))).toBe(false);
});

it('preserves the original financial record after a lost response and only retries its same ID deliberately', async () => {
  const normal = fetcher.getMockImplementation()!;
  let first = true;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === '/v1/plan/audit') return reply({ events: [] });
    if (path === '/v1/plan/cash-events') {
      if (first) { first = false; throw new Error('Synthetic response lost'); }
      return reply({ recorded: false, event_id: JSON.parse(String(init?.body)).event_id, summary });
    }
    return normal(path, init);
  });
  await openUpdate('savings_deposit', 'goal', '25.50');
  fireEvent.click(screen.getByRole('button', { name: 'Review update' }));
  fireEvent.click(screen.getByLabelText('I confirm this already happened outside GoalGuard.'));
  fireEvent.click(screen.getByRole('button', { name: 'Record this update' }));
  await screen.findByText(/Check whether this record was saved/);
  expect(posts('/v1/plan/cash-events')).toHaveLength(1);
  expect(screen.queryByRole('button', { name: 'Retry this same record' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Check recorded status' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Retry this same record' }));
  await screen.findByText(/already recorded/);
  const bodies = posts('/v1/plan/cash-events').map(([, init]) => JSON.parse(init.body));
  expect(bodies).toHaveLength(2); expect(bodies[1]).toEqual(bodies[0]);
  expect(bodies[0].amount_cents).toBe(2550);
});

it('resolves a saved record from audit without repeating the mutation', async () => {
  const normal = fetcher.getMockImplementation()!;
  let payload: Record<string, unknown>;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === '/v1/plan/cash-events') { payload = JSON.parse(String(init?.body)); throw new Error('Synthetic reply lost'); }
    if (path === '/v1/plan/audit') return reply({ events: [{ event: 'cash_recorded', details: payload }] });
    return normal(path, init);
  });
  await openUpdate('external_inflow', '', '10');
  fireEvent.click(screen.getByRole('button', { name: 'Review update' }));
  fireEvent.click(screen.getByLabelText('I confirm this already happened outside GoalGuard.'));
  fireEvent.click(screen.getByRole('button', { name: 'Record this update' }));
  await screen.findByRole('button', { name: 'Check recorded status' });
  fireEvent.click(screen.getByRole('button', { name: 'Check recorded status' }));
  await screen.findByText(/already recorded/);
  expect(posts('/v1/plan/cash-events')).toHaveLength(1);
  expect(JSON.parse(String(posts('/v1/plan/cash-events')[0]?.[1]?.body)).reference_id).toBeNull();
});

it('discards a late AI reply after locking and requires fresh consent after unlocking', async () => {
  let finish!: (value: Response) => void;
  const pending = new Promise<Response>(resolve => { finish = resolve; });
  const normal = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/draft' ? pending : normal(path, init));
  await openDraft();
  fireEvent.click(screen.getByLabelText('I agree to send this sample to Google Gemini for drafting.'));
  fireEvent.click(screen.getByRole('button', { name: 'Create sample AI draft' }));
  await waitFor(() => expect(posts('/v1/plan/draft')).toHaveLength(1));
  fireEvent.click(screen.getByRole('button', { name: 'Lock workspace' }));
  await screen.findByLabelText('Owner key');
  await act(async () => { finish(reply({ status: 'draft_ready', preview, plan: spec })); });
  fill('Owner key', 'synthetic-owner-key');
  fireEvent.click(screen.getByRole('button', { name: 'Unlock workspace' }));
  await screen.findByText('Try AI drafting with sample data', { exact: true });
  expect(screen.queryByRole('button', { name: 'Confirm this plan' })).toBeNull();
  expect(screen.getByLabelText('I agree to send this sample to Google Gemini for drafting.')).toHaveProperty('checked', false);
  expect(posts('/v1/plan/draft')).toHaveLength(1);
});

it('invalidates a previous AI preview when a new draft needs manual entry', async () => {
  const normal = fetcher.getMockImplementation()!;
  let count = 0;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/draft'
    ? ++count === 1 ? reply({ status: 'draft_ready', preview })
      : reply({ status: 'needs_manual_entry', questions: ['Use manual entry to verify the dates.'] }) : normal(path, init));
  await openDraft();
  fireEvent.click(screen.getByLabelText('I agree to send this sample to Google Gemini for drafting.'));
  fireEvent.click(screen.getByRole('button', { name: 'Create sample AI draft' }));
  await screen.findByRole('button', { name: 'Confirm this plan' });
  fireEvent.click(screen.getByRole('button', { name: 'Create sample AI draft' }));
  await screen.findByText('Use manual entry to verify the dates.');
  expect(screen.queryByRole('button', { name: 'Confirm this plan' })).toBeNull();
  expect(posts('/v1/plan/confirm')).toHaveLength(0);
});

it.each([
  ['income', 'pay'], ['savings_deposit', 'goal'], ['external_inflow', ''], ['external_outflow', ''], ['refund', 'captured-cart'],
])('records %s through the existing cash-event contract with a new unique identity', async (kind, reference) => {
  view.purchases = [{ id: 'captured-cart', agent: 'sample-agent', state: 'captured', amount_cents: 10000,
    cart_hash: 'sample-cart', expires_at: 0, permit: null, operation_id: null, order_id: null,
    cart: { merchant: 'Synthetic catalog', currency: 'USD', shipping_cents: 0, tax_cents: 0,
      items: [{ sku: 'mic-budget', quantity: 1, unit_cents: 10000 }] } }];
  const normal = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/cash-events'
    ? reply({ recorded: true, event_id: JSON.parse(String(init?.body)).event_id, summary }) : normal(path, init));
  await openUpdate(kind, reference, '12.34');
  expect(screen.queryByText('Try AI drafting with sample data', { exact: true })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Review update' }));
  fireEvent.click(screen.getByLabelText('I confirm this already happened outside GoalGuard.'));
  fireEvent.click(screen.getByRole('button', { name: 'Record this update' }));
  await screen.findByText(/Financial update recorded/);
  const body = JSON.parse(String(posts('/v1/plan/cash-events')[0]?.[1]?.body));
  expect(body).toEqual({ kind, reference_id: reference || null, amount_cents: 1234, event_id: expect.any(String) });
  expect(body.event_id).toMatch(/^[\da-f-]{36}$/);
});

it('rejects zero and fractional cents locally and supports editing a reviewed record before sending', async () => {
  await openUpdate('bill_payment', 'bill', '0');
  fireEvent.click(screen.getByRole('button', { name: 'Review update' }));
  await screen.findByText('Enter an amount greater than zero.');
  fill('Amount (USD)', '1.001');
  fireEvent.click(screen.getByRole('button', { name: 'Review update' }));
  await screen.findByText(/at most two decimal places/);
  expect(posts('/v1/plan/cash-events')).toHaveLength(0);
  fill('Amount (USD)', '2');
  fireEvent.click(screen.getByRole('button', { name: 'Review update' }));
  fireEvent.click(screen.getByRole('button', { name: 'Edit this update' }));
  expect(screen.queryByRole('heading', { name: 'Review this financial record' })).toBeNull();
  expect(screen.getByLabelText('Amount (USD)')).toHaveProperty('value', '2');
});

it('shows missing references and never offers an unlinked refund or savings record', async () => {
  view.plan = { ...summary, spec: { ...spec, bills: [], goal: null, next_income: null } };
  render(<Setup />);
  fireEvent.click(await screen.findByText('Record a financial update', { exact: true }));
  for (const kind of ['bill_payment', 'savings_deposit', 'income', 'refund']) {
    fill('Activity', kind);
    expect(screen.getByText(/No matching record is available/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Review update' })).toHaveProperty('disabled', true);
  }
  expect(posts('/v1/plan/cash-events')).toHaveLength(0);
});

it('retains correctable input after an explicit server validation rejection', async () => {
  const normal = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/cash-events'
    ? reply({ reason: 'invalid_cash_event', message: 'Payment must fit the unpaid bill balance.' }, 409) : normal(path, init));
  await openUpdate();
  fireEvent.click(screen.getByRole('button', { name: 'Review update' }));
  fireEvent.click(screen.getByLabelText('I confirm this already happened outside GoalGuard.'));
  fireEvent.click(screen.getByRole('button', { name: 'Record this update' }));
  await screen.findByText('Payment must fit the unpaid bill balance.');
  expect(screen.queryByRole('button', { name: 'Check recorded status' })).toBeNull();
  expect(screen.getByLabelText('Amount (USD)')).toHaveProperty('value', '40');
  expect(screen.getByRole('button', { name: 'Review update' })).toHaveProperty('disabled', false);
  expect(posts('/v1/plan/cash-events')).toHaveLength(1);
});

it.each([{ status: 'draft_ready', preview: {} }, { status: 'unexpected' }])('keeps malformed AI replies out of confirmation: %j', async result => {
  const normal = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/draft' ? reply(result) : normal(path, init));
  await openDraft();
  fireEvent.click(screen.getByLabelText('I agree to send this sample to Google Gemini for drafting.'));
  fireEvent.click(screen.getByRole('button', { name: 'Create sample AI draft' }));
  await screen.findByRole('alert');
  expect(screen.queryByRole('button', { name: 'Confirm this plan' })).toBeNull();
  expect(posts('/v1/plan/confirm')).toHaveLength(0);
});

it('shows recorded cash terms and their identity in Timeline for review after a page reload', async () => {
  view.plan = { ...summary, spec };
  view.events = [{ id: 'cash-event', at: 1792749600, event: 'cash_recorded', purchase_id: null,
    details: { kind: 'bill_payment', amount_cents: 4000, reference_id: 'bill', event_id: 'owner-record-id' } }];
  render(<Setup />); await screen.findByRole('heading', { name: 'Your financial plan' });
  fireEvent.click(screen.getByRole('button', { name: 'Timeline' }));
  expect(screen.getByText(/bill payment: \$40.00/)).toBeTruthy();
  expect(screen.getByText(/Record ID: owner-record-id/)).toBeTruthy();
  expect(screen.getByText(/Linked record: bill/)).toBeTruthy();
});

it('retains an uncertain cash record across locking, discards the old reply and never replays after unlocking', async () => {
  const normal = fetcher.getMockImplementation()!;
  let payload: Record<string, unknown>;
  let finish!: (value: Response) => void;
  const pending = new Promise<Response>(resolve => { finish = resolve; });
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === '/v1/plan/cash-events') { payload = JSON.parse(String(init?.body)); return pending; }
    if (path === '/v1/plan/audit') return reply({ events: [{ event: 'cash_recorded', details: payload }] });
    return normal(path, init);
  });
  await openUpdate();
  fireEvent.click(screen.getByRole('button', { name: 'Review update' }));
  fireEvent.click(screen.getByLabelText('I confirm this already happened outside GoalGuard.'));
  fireEvent.click(screen.getByRole('button', { name: 'Record this update' }));
  await waitFor(() => expect(posts('/v1/plan/cash-events')).toHaveLength(1));
  fireEvent.click(screen.getByRole('button', { name: 'Lock workspace' }));
  await screen.findByLabelText('Owner key');
  await act(async () => { finish(reply({ recorded: true, event_id: payload.event_id, summary })); });
  fill('Owner key', 'synthetic-owner-key'); fireEvent.click(screen.getByRole('button', { name: 'Unlock workspace' }));
  fireEvent.click(await screen.findByText('Record a financial update', { exact: true }));
  expect(screen.queryByText(/Financial update recorded/)).toBeNull();
  expect(screen.getByLabelText('I confirm this already happened outside GoalGuard.')).toHaveProperty('checked', false);
  fireEvent.click(screen.getByRole('button', { name: 'Check recorded status' }));
  await screen.findByText(/already recorded/);
  expect(posts('/v1/plan/cash-events')).toHaveLength(1);
});

it('keeps retry disabled when recorded status cannot be read or returns conflicting terms', async () => {
  const normal = fetcher.getMockImplementation()!;
  let payload: Record<string, unknown>;
  let check = 0;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === '/v1/plan/cash-events') { payload = JSON.parse(String(init?.body)); return reply({}); }
    if (path === '/v1/plan/audit') return ++check === 1 ? reply({})
      : reply({ events: [{ event: 'cash_recorded', details: { ...payload, amount_cents: 1 } }] });
    return normal(path, init);
  });
  await openUpdate();
  fireEvent.click(screen.getByRole('button', { name: 'Review update' }));
  fireEvent.click(screen.getByLabelText('I confirm this already happened outside GoalGuard.'));
  fireEvent.click(screen.getByRole('button', { name: 'Record this update' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Check recorded status' }));
  await screen.findByText(/Recorded status is unavailable/);
  expect(screen.queryByRole('button', { name: 'Retry this same record' })).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Check recorded status' }));
  await screen.findByText(/different terms/);
  expect(screen.queryByRole('button', { name: 'Retry this same record' })).toBeNull();
  expect(posts('/v1/plan/cash-events')).toHaveLength(1);
});

it('accepts the real backend null blocker contract for a ready AI preview', async () => {
  const normal = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/draft'
    ? reply({ status: 'draft_ready', preview: { ...preview, activation_blocked_by: null } }) : normal(path, init));
  await openDraft();
  fireEvent.click(screen.getByLabelText('I agree to send this sample to Google Gemini for drafting.'));
  fireEvent.click(screen.getByRole('button', { name: 'Create sample AI draft' }));
  expect(await screen.findByRole('button', { name: 'Confirm this plan' })).toHaveProperty('disabled', false);
  expect(posts('/v1/plan/confirm')).toHaveLength(0);
});

it('switches a confirmed initial draft to revision mode for the next deliberate preview', async () => {
  const normal = fetcher.getMockImplementation()!;
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => {
    if (path === '/v1/plan/draft') return reply({ status: 'draft_ready', preview });
    if (path === '/v1/plan/confirm') { view.plan = { ...summary, spec }; return reply(summary); }
    if (path === '/v1/plan/preview') return reply({ ...preview, mode: JSON.parse(String(init?.body)).mode });
    return normal(path, init);
  });
  await openDraft();
  fireEvent.click(screen.getByLabelText('I agree to send this sample to Google Gemini for drafting.'));
  fireEvent.click(screen.getByRole('button', { name: 'Create sample AI draft' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Confirm this plan' }));
  await screen.findByRole('heading', { name: 'Your financial plan' });
  expect(screen.getByLabelText('Plan change')).toHaveProperty('value', 'revise');
  expect(JSON.parse(String(posts('/v1/plan/confirm')[0]?.[1]?.body)).mode).toBe('activate');
  fireEvent.click(screen.getByRole('button', { name: 'Preview protections' }));
  await waitFor(() => expect(posts('/v1/plan/preview')).toHaveLength(1));
  expect(JSON.parse(String(posts('/v1/plan/preview')[0]?.[1]?.body)).mode).toBe('revise');
});

it('does not let an AI request overlap an in-progress manual plan preview', async () => {
  const normal = fetcher.getMockImplementation()!;
  let finish!: (value: Response) => void;
  const pending = new Promise<Response>(resolve => { finish = resolve; });
  fetcher.mockImplementation(async (path: string, init?: RequestInit) => path === '/v1/plan/preview' ? pending : normal(path, init));
  await openDraft();
  fill('Plan name', spec.title); fill('Timezone', 'UTC'); fill('Current cash (USD)', '600'); fill('Cash buffer (USD)', '50');
  fill('Next payday', '2026-11-05'); fill('Expected income (USD)', '400');
  fireEvent.click(screen.getByLabelText('I agree to send this sample to Google Gemini for drafting.'));
  fireEvent.click(screen.getByRole('button', { name: 'Preview protections' }));
  const create = screen.getByRole('button', { name: 'Create sample AI draft' });
  try {
    expect(create).toHaveProperty('disabled', true);
    fireEvent.click(create);
    expect(posts('/v1/plan/draft')).toHaveLength(0);
  } finally { await act(async () => { finish(reply(preview)); }); }
});
